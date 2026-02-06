import time
from datetime import datetime

import yfinance as yf

from config import YFINANCE_BATCH_SIZE, YFINANCE_BATCH_DELAY_SEC
from data_store import DataStore
from models import Stock, FetchLog, FetchStatus, DataSource
from ticker_mapping import nse_to_yahoo
from utils import setup_logger, RateLimiter

logger = setup_logger(__name__, "fetch_nifty500_list.log")


def get_nifty500_symbols() -> list[str]:
    """Fetch Nifty 500 constituent symbols using niftystocks package."""
    try:
        from niftystocks import ns
        symbols = ns.get_nifty500()
        if symbols and len(symbols) > 400:
            logger.info(f"Got {len(symbols)} symbols from niftystocks")
            return symbols
    except Exception as e:
        logger.warning(f"niftystocks failed: {e}")

    # Fallback: try nselib
    try:
        from nselib import capital_market
        df = capital_market.market_watch_all_indices()
        # nselib may not directly give Nifty 500 constituents in a clean way;
        # try the index constituents endpoint
        logger.warning("Falling back to nselib for Nifty 500 list")
        # This is less reliable, but worth a try
        from nselib.indices import constituent_stock_list
        result = constituent_stock_list(
            index_category="BroadMarketIndices", index_name="Nifty 500"
        )
        if hasattr(result, "Symbol"):
            syms = result["Symbol"].tolist()
            logger.info(f"Got {len(syms)} symbols from nselib")
            return syms
    except Exception as e:
        logger.warning(f"nselib fallback also failed: {e}")

    raise RuntimeError("Could not fetch Nifty 500 constituent list from any source")


def enrich_stock_info(
    symbols: list[str], store: DataStore
) -> list[Stock]:
    """Fetch company name, sector, industry from yfinance for each symbol."""
    stocks: list[Stock] = []
    rate_limiter = RateLimiter(min_delay=1.0, max_delay=2.0)
    failed: list[str] = []

    for i, symbol in enumerate(symbols):
        yahoo_sym = nse_to_yahoo(symbol)
        try:
            rate_limiter.wait()
            ticker = yf.Ticker(yahoo_sym)
            info = ticker.info or {}
            stock = Stock(
                symbol=symbol,
                yahoo_symbol=yahoo_sym,
                company_name=info.get("longName") or info.get("shortName") or symbol,
                sector=info.get("sector"),
                industry=info.get("industry"),
                last_updated=datetime.now(),
            )
            stocks.append(stock)
            if (i + 1) % 50 == 0:
                logger.info(f"Enriched {i + 1}/{len(symbols)} stocks")
                # Save intermediate progress
                store.upsert_stocks(stocks[-50:])
        except Exception as e:
            logger.warning(f"Failed to enrich {symbol}: {e}")
            failed.append(symbol)
            # Still add the stock with minimal info
            stocks.append(
                Stock(
                    symbol=symbol,
                    yahoo_symbol=yahoo_sym,
                    company_name=symbol,
                    last_updated=datetime.now(),
                )
            )

    if failed:
        logger.warning(f"Failed to enrich {len(failed)} stocks: {failed[:10]}...")

    return stocks


def run(store: DataStore, skip_enrichment: bool = False) -> dict:
    """Fetch Nifty 500 list and store it.

    Returns summary dict with counts.
    """
    started = datetime.now()
    logger.info("Fetching Nifty 500 constituent list...")

    symbols = get_nifty500_symbols()
    logger.info(f"Found {len(symbols)} Nifty 500 constituents")

    if skip_enrichment:
        stocks = [
            Stock(
                symbol=s,
                yahoo_symbol=nse_to_yahoo(s),
                company_name=s,
                last_updated=datetime.now(),
            )
            for s in symbols
        ]
    else:
        logger.info("Enriching stocks with company info from yfinance (this takes a few minutes)...")
        stocks = enrich_stock_info(symbols, store)

    count = store.upsert_stocks(stocks)
    logger.info(f"Stored {count} stocks in database")

    store.log_fetch(
        FetchLog(
            script_name="fetch_nifty500_list",
            symbol=None,
            status=FetchStatus.SUCCESS,
            records_fetched=count,
            source=DataSource.NIFTYSTOCKS,
            started_at=started,
            completed_at=datetime.now(),
        )
    )

    return {"total": len(symbols), "stored": count}


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store)
        print(f"Done. Stored {result['stored']}/{result['total']} stocks.")
    finally:
        store.close()
