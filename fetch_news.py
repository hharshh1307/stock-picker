import re
import time
from datetime import datetime

import feedparser
from gnews import GNews

from config import (
    GNEWS_DELAY_SEC,
    GNEWS_MAX_RESULTS,
    GNEWS_BATCH_SIZE,
    GNEWS_LONG_PAUSE_SEC,
    RSS_FEEDS,
)
from data_store import DataStore
from models import NewsArticle, FetchLog, FetchStatus, DataSource
from utils import setup_logger, RateLimiter

logger = setup_logger(__name__, "fetch_news.log")


def fetch_gnews_for_stock(
    gnews_client: GNews, symbol: str, company_name: str
) -> list[NewsArticle]:
    """Fetch news articles for a single stock via GNews."""
    articles: list[NewsArticle] = []
    query = f"{company_name} stock NSE"

    try:
        results = gnews_client.get_news(query)
        if not results:
            return articles

        for item in results:
            published = None
            if item.get("published date"):
                try:
                    published = datetime.strptime(
                        item["published date"], "%a, %d %b %Y %H:%M:%S %Z"
                    )
                except (ValueError, TypeError):
                    pass

            articles.append(
                NewsArticle(
                    symbol=symbol,
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source_name=item.get("publisher", {}).get("title", "Google News"),
                    published_at=published,
                    description=item.get("description"),
                    fetched_at=datetime.now(),
                )
            )
    except Exception as e:
        logger.warning(f"GNews failed for {symbol} ({company_name}): {e}")

    return articles


def fetch_rss_news(store: DataStore) -> int:
    """Fetch news from RSS feeds and match to stocks by symbol/company name."""
    all_stocks = store.get_all_stocks()
    # Build lookup sets for matching
    symbol_set = {s.symbol.upper() for s in all_stocks}
    name_lookup: dict[str, str] = {}
    for s in all_stocks:
        # Map lowercase company name words to symbol for matching
        name_lookup[s.symbol.upper()] = s.symbol
        if s.company_name and s.company_name != s.symbol:
            # Use first 2 meaningful words of company name
            words = s.company_name.upper().split()
            if words:
                name_lookup[words[0]] = s.symbol

    total_articles = 0

    for feed_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            logger.info(f"RSS feed '{feed_name}': {len(feed.entries)} entries")

            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                published = None
                if entry.get("published_parsed"):
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except (TypeError, ValueError):
                        pass

                # Match to stocks using word-boundary regex to avoid
                # false positives (e.g., "ITI" matching inside "ATTENTION")
                text_upper = (title + " " + summary).upper()
                matched_symbols: set[str] = set()
                for key, sym in name_lookup.items():
                    if len(key) < 4:
                        # Short keys need strict word-boundary match
                        if re.search(r'\b' + re.escape(key) + r'\b', text_upper):
                            matched_symbols.add(sym)
                    elif key in text_upper:
                        matched_symbols.add(sym)

                # If no match, store as general market news
                if not matched_symbols:
                    matched_symbols = {"_MARKET"}

                for sym in matched_symbols:
                    article = NewsArticle(
                        symbol=sym,
                        title=title,
                        url=link,
                        source_name=feed_name,
                        published_at=published,
                        description=summary[:500] if summary else None,
                        fetched_at=datetime.now(),
                    )
                    total_articles += 1
                    store.upsert_news([article])

        except Exception as e:
            logger.warning(f"Failed to parse RSS feed '{feed_name}': {e}")

    return total_articles


def run(
    store: DataStore,
    symbols: list[str] | None = None,
    gnews_only: bool = False,
    rss_only: bool = False,
    max_stocks: int | None = None,
) -> dict:
    """Fetch news from GNews and/or RSS feeds.

    Args:
        store: DataStore instance
        symbols: Optional list of NSE symbols for GNews queries.
        gnews_only: Only fetch from GNews.
        rss_only: Only fetch from RSS feeds.
        max_stocks: Limit number of stocks for GNews queries.
    """
    started = datetime.now()
    gnews_count = 0
    rss_count = 0

    # RSS feeds
    if not gnews_only:
        logger.info("Fetching RSS feed news...")
        rss_count = fetch_rss_news(store)
        logger.info(f"RSS: {rss_count} articles processed")

    # GNews per-stock
    if not rss_only:
        all_stocks = store.get_all_stocks()
        if symbols:
            stock_map = {s.symbol: s for s in all_stocks}
            stocks = [stock_map[sym] for sym in symbols if sym in stock_map]
        else:
            stocks = all_stocks

        if max_stocks:
            stocks = stocks[:max_stocks]

        logger.info(f"Fetching GNews for {len(stocks)} stocks...")
        gnews_client = GNews(language="en", country="IN", max_results=GNEWS_MAX_RESULTS)
        rate_limiter = RateLimiter(min_delay=GNEWS_DELAY_SEC, max_delay=GNEWS_DELAY_SEC + 2.0)

        for i, stock in enumerate(stocks):
            rate_limiter.wait()
            articles = fetch_gnews_for_stock(gnews_client, stock.symbol, stock.company_name)
            if articles:
                store.upsert_news(articles)
                gnews_count += len(articles)

            if (i + 1) % GNEWS_BATCH_SIZE == 0:
                logger.info(f"GNews progress: {i + 1}/{len(stocks)} stocks, {gnews_count} articles")
                time.sleep(GNEWS_LONG_PAUSE_SEC)

    total = gnews_count + rss_count
    logger.info(
        f"=== fetch_news Summary ===\n"
        f"  GNews articles: {gnews_count}\n"
        f"  RSS articles: {rss_count}\n"
        f"  Total: {total}\n"
        f"  Duration: {datetime.now() - started}"
    )

    store.log_fetch(
        FetchLog(
            script_name="fetch_news",
            symbol=None,
            status=FetchStatus.SUCCESS,
            records_fetched=total,
            source=DataSource.GNEWS if not rss_only else DataSource.RSS_FEED,
            started_at=started,
            completed_at=datetime.now(),
        )
    )

    return {"gnews": gnews_count, "rss": rss_count, "total": total}


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store, rss_only=True)
        print(f"Done. {result['total']} news articles.")
    finally:
        store.close()
