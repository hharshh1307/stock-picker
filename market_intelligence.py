import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from data_store import DataStore
from utils import setup_logger

logger = setup_logger(__name__, "market_intelligence.log")


# --- Sector analysis helpers ---

def get_sector_stocks(store: DataStore) -> dict[str, list[dict]]:
    """Group stocks by sector. Returns {sector: [{symbol, company_name, industry}, ...]}."""
    rows = store.conn.execute(
        "SELECT symbol, company_name, sector, industry FROM stocks WHERE sector IS NOT NULL ORDER BY sector, symbol"
    ).fetchall()
    sectors: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sectors[r["sector"]].append({
            "symbol": r["symbol"],
            "company_name": r["company_name"],
            "industry": r["industry"],
        })
    return dict(sectors)


def get_sector_performance(store: DataStore, days: int = 30) -> list[dict]:
    """Calculate average price change % per sector over the last N days.

    Returns sorted list of {sector, avg_change_pct, stock_count, top_gainers, top_losers}.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    today = date.today().isoformat()

    # Get earliest and latest price per stock in the window
    rows = store.conn.execute(
        """
        WITH price_range AS (
            SELECT p.symbol, s.sector,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date ASC) as start_price,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as end_price
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
        )
        SELECT DISTINCT symbol, sector, start_price, end_price,
               CASE WHEN start_price > 0 THEN ((end_price - start_price) / start_price) * 100 ELSE 0 END as change_pct
        FROM price_range
        WHERE start_price > 0
        ORDER BY sector, change_pct DESC
        """,
        (cutoff,),
    ).fetchall()

    sector_data: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        sector_data[r["sector"]].append({
            "symbol": r["symbol"],
            "change_pct": r["change_pct"],
            "start_price": r["start_price"],
            "end_price": r["end_price"],
        })

    results = []
    for sector, stocks in sector_data.items():
        changes = [s["change_pct"] for s in stocks]
        avg_change = sum(changes) / len(changes) if changes else 0
        sorted_stocks = sorted(stocks, key=lambda x: x["change_pct"], reverse=True)
        results.append({
            "sector": sector,
            "avg_change_pct": round(avg_change, 2),
            "stock_count": len(stocks),
            "top_gainers": sorted_stocks[:3],
            "top_losers": sorted_stocks[-3:],
        })

    results.sort(key=lambda x: x["avg_change_pct"], reverse=True)
    return results


def get_top_movers(store: DataStore, days: int = 30, limit: int = 10) -> dict[str, list[dict]]:
    """Get top gaining and losing stocks over the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rows = store.conn.execute(
        """
        WITH price_range AS (
            SELECT p.symbol, s.company_name, s.sector,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date ASC) as start_price,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as end_price,
                   FIRST_VALUE(p.volume) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as latest_volume
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
        )
        SELECT DISTINCT symbol, company_name, sector, start_price, end_price, latest_volume,
               CASE WHEN start_price > 0 THEN ((end_price - start_price) / start_price) * 100 ELSE 0 END as change_pct
        FROM price_range
        WHERE start_price > 0
        """,
        (cutoff,),
    ).fetchall()

    all_stocks = [dict(r) for r in rows]
    all_stocks.sort(key=lambda x: x["change_pct"], reverse=True)

    return {
        "gainers": all_stocks[:limit],
        "losers": all_stocks[-limit:][::-1],
    }


def get_volume_spikes(store: DataStore, days: int = 5, threshold: float = 2.0) -> list[dict]:
    """Find stocks with recent volume significantly above their average.

    Returns stocks where recent avg volume > threshold * 30-day avg volume.
    """
    recent_cutoff = (date.today() - timedelta(days=days)).isoformat()
    avg_cutoff = (date.today() - timedelta(days=60)).isoformat()

    rows = store.conn.execute(
        """
        WITH recent_vol AS (
            SELECT symbol, AVG(volume) as recent_avg_vol
            FROM prices
            WHERE date >= ?
            GROUP BY symbol
        ),
        historical_vol AS (
            SELECT symbol, AVG(volume) as hist_avg_vol
            FROM prices
            WHERE date >= ? AND date < ?
            GROUP BY symbol
        )
        SELECT r.symbol, s.company_name, s.sector,
               r.recent_avg_vol, h.hist_avg_vol,
               r.recent_avg_vol / h.hist_avg_vol as vol_ratio
        FROM recent_vol r
        JOIN historical_vol h ON r.symbol = h.symbol
        JOIN stocks s ON r.symbol = s.symbol
        WHERE h.hist_avg_vol > 0 AND r.recent_avg_vol / h.hist_avg_vol > ?
        ORDER BY vol_ratio DESC
        LIMIT 15
        """,
        (recent_cutoff, avg_cutoff, recent_cutoff, threshold),
    ).fetchall()

    return [dict(r) for r in rows]


def get_financial_highlights(store: DataStore) -> list[dict]:
    """Find stocks with notable quarterly financial performance.

    Looks at most recent quarter's revenue growth and profitability.
    """
    # Get latest 2 quarters per stock for comparison
    rows = store.conn.execute(
        """
        SELECT symbol, period_ending, data_json
        FROM quarterly_financials
        WHERE statement_type = 'income'
        ORDER BY symbol, period_ending DESC
        """
    ).fetchall()

    # Group by symbol, take latest 2 quarters
    stock_quarters: dict[str, list] = defaultdict(list)
    for r in rows:
        if len(stock_quarters[r["symbol"]]) < 2:
            stock_quarters[r["symbol"]].append({
                "period": r["period_ending"],
                "data": json.loads(r["data_json"]),
            })

    highlights = []
    for symbol, quarters in stock_quarters.items():
        if not quarters:
            continue
        latest = quarters[0]["data"]

        revenue = latest.get("Total Revenue") or latest.get("Operating Revenue")
        net_income = latest.get("Net Income") or latest.get("Net Income From Continuing Operation Net Minority Interest")
        ebitda = latest.get("Normalized EBITDA") or latest.get("EBITDA")

        if not revenue or not net_income or revenue == 0:
            continue

        profit_margin = (net_income / revenue * 100)
        # Filter out extreme outliers (one-time gains, accounting anomalies)
        if abs(profit_margin) > 100:
            continue

        # QoQ growth if we have 2 quarters
        revenue_growth = None
        if len(quarters) == 2:
            prev = quarters[1]["data"]
            prev_revenue = prev.get("Total Revenue") or prev.get("Operating Revenue")
            if prev_revenue and prev_revenue > 0:
                revenue_growth = ((revenue - prev_revenue) / prev_revenue) * 100

        stock = store.get_stock(symbol)
        highlights.append({
            "symbol": symbol,
            "company_name": stock.company_name if stock else symbol,
            "sector": stock.sector if stock else None,
            "period": quarters[0]["period"],
            "revenue": revenue,
            "net_income": net_income,
            "ebitda": ebitda,
            "profit_margin": round(profit_margin, 2),
            "revenue_growth_qoq": round(revenue_growth, 2) if revenue_growth is not None else None,
        })

    return highlights


def get_market_breadth(store: DataStore, days: int = 30) -> dict:
    """Calculate market breadth: % of stocks advancing vs declining."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rows = store.conn.execute(
        """
        WITH price_range AS (
            SELECT p.symbol,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date ASC) as start_price,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as end_price
            FROM prices p
            WHERE p.date >= ?
        )
        SELECT DISTINCT symbol, start_price, end_price
        FROM price_range
        WHERE start_price > 0
        """,
        (cutoff,),
    ).fetchall()

    advancing = sum(1 for r in rows if r["end_price"] > r["start_price"])
    declining = sum(1 for r in rows if r["end_price"] < r["start_price"])
    unchanged = sum(1 for r in rows if r["end_price"] == r["start_price"])
    total = len(rows)

    return {
        "total": total,
        "advancing": advancing,
        "declining": declining,
        "unchanged": unchanged,
        "advance_pct": round(advancing / total * 100, 1) if total else 0,
        "decline_pct": round(declining / total * 100, 1) if total else 0,
        "breadth_ratio": round(advancing / declining, 2) if declining else 0,
    }


def get_recent_news_summary(store: DataStore, limit: int = 15) -> list[dict]:
    """Get the most recent news articles that could influence the market."""
    rows = store.conn.execute(
        """
        SELECT symbol, title, source_name, published_at, description
        FROM news
        WHERE symbol != '_MARKET'
        ORDER BY published_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_market_news(store: DataStore, limit: int = 10) -> list[dict]:
    """Get general market-level news."""
    rows = store.conn.execute(
        """
        SELECT title, source_name, published_at, description
        FROM news
        WHERE symbol = '_MARKET'
        ORDER BY published_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Main intelligence report ---

def generate_report(store: DataStore) -> str:
    """Generate the full market intelligence report.

    Produces 8-10 actionable insights based on all available data.
    """
    lines: list[str] = []

    def section(title: str) -> None:
        lines.append(f"\n{'='*60}")
        lines.append(f"  {title}")
        lines.append(f"{'='*60}")

    def point(num: int, text: str) -> None:
        lines.append(f"\n  [{num}] {text}")

    lines.append(f"\n  NIFTY 500 MARKET INTELLIGENCE REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    point_num = 0

    # 1. Market Breadth
    section("MARKET BREADTH")
    breadth_30d = get_market_breadth(store, days=30)
    breadth_7d = get_market_breadth(store, days=7)
    point_num += 1
    if breadth_30d["total"] > 0:
        sentiment = "BULLISH" if breadth_30d["breadth_ratio"] > 1.2 else "BEARISH" if breadth_30d["breadth_ratio"] < 0.8 else "NEUTRAL"
        point(point_num,
            f"Market Sentiment: {sentiment}\n"
            f"      30-Day: {breadth_30d['advancing']} advancing / {breadth_30d['declining']} declining "
            f"(ratio: {breadth_30d['breadth_ratio']})\n"
            f"       7-Day: {breadth_7d['advancing']} advancing / {breadth_7d['declining']} declining "
            f"(ratio: {breadth_7d['breadth_ratio']})"
        )

    # 2-3. Trending Sectors
    section("TRENDING SECTORS (30-Day Performance)")
    perf_30d = get_sector_performance(store, days=30)
    if perf_30d:
        point_num += 1
        top_sectors = perf_30d[:5]
        sector_lines = []
        for s in top_sectors:
            gainers_str = ", ".join(f"{g['symbol']}(+{g['change_pct']:.1f}%)" for g in s["top_gainers"][:2])
            sector_lines.append(
                f"      {s['sector']:30s}  avg: {'+' if s['avg_change_pct']>0 else ''}{s['avg_change_pct']:6.2f}%  "
                f"({s['stock_count']} stocks)  Leaders: {gainers_str}"
            )
        point(point_num,
            f"Top Performing Sectors:\n" + "\n".join(sector_lines)
        )

        point_num += 1
        bottom_sectors = perf_30d[-3:]
        sector_lines = []
        for s in bottom_sectors:
            losers_str = ", ".join(f"{g['symbol']}({g['change_pct']:.1f}%)" for g in s["top_losers"][:2])
            sector_lines.append(
                f"      {s['sector']:30s}  avg: {s['avg_change_pct']:6.2f}%  "
                f"({s['stock_count']} stocks)  Laggards: {losers_str}"
            )
        point(point_num,
            f"Underperforming Sectors:\n" + "\n".join(sector_lines)
        )

    # 4-5. Top Movers
    section("TOP STOCK MOVERS (30-Day)")
    movers = get_top_movers(store, days=30, limit=5)
    if movers.get("gainers"):
        point_num += 1
        gainer_lines = []
        for g in movers["gainers"]:
            gainer_lines.append(
                f"      {g['symbol']:15s} {g.get('company_name','')[:25]:25s}  +{g['change_pct']:.1f}%  [{g.get('sector','-')}]"
            )
        point(point_num, f"Top Gainers:\n" + "\n".join(gainer_lines))

    if movers.get("losers"):
        point_num += 1
        loser_lines = []
        for g in movers["losers"]:
            loser_lines.append(
                f"      {g['symbol']:15s} {g.get('company_name','')[:25]:25s}  {g['change_pct']:.1f}%  [{g.get('sector','-')}]"
            )
        point(point_num, f"Top Losers:\n" + "\n".join(loser_lines))

    # 6. Volume Spikes (unusual activity)
    section("UNUSUAL VOLUME ACTIVITY")
    spikes = get_volume_spikes(store, days=5, threshold=2.0)
    if spikes:
        point_num += 1
        spike_lines = []
        for s in spikes[:7]:
            spike_lines.append(
                f"      {s['symbol']:15s} [{s.get('sector','-')}]  "
                f"Volume {s['vol_ratio']:.1f}x above average"
            )
        point(point_num,
            f"Stocks with Unusual Volume (last 5 days vs 60-day avg):\n" + "\n".join(spike_lines)
        )
    else:
        point_num += 1
        point(point_num, "No significant volume spikes detected in the last 5 days.")

    # 7. Financial Highlights
    section("QUARTERLY FINANCIAL STANDOUTS")
    highlights = get_financial_highlights(store)
    if highlights:
        # Top by revenue growth QoQ
        with_growth = [h for h in highlights if h["revenue_growth_qoq"] is not None]
        with_growth.sort(key=lambda x: x["revenue_growth_qoq"], reverse=True)
        if with_growth:
            point_num += 1
            growth_lines = []
            for h in with_growth[:5]:
                growth_lines.append(
                    f"      {h['symbol']:15s} Revenue Growth: {'+' if h['revenue_growth_qoq']>0 else ''}{h['revenue_growth_qoq']:.1f}% QoQ  "
                    f"Margin: {h['profit_margin']:.1f}%  [{h.get('sector','-')}]"
                )
            point(point_num, f"Fastest Revenue Growth (QoQ):\n" + "\n".join(growth_lines))

        # Top by profit margin
        high_margin = sorted(highlights, key=lambda x: x["profit_margin"], reverse=True)
        point_num += 1
        margin_lines = []
        for h in high_margin[:5]:
            margin_lines.append(
                f"      {h['symbol']:15s} Profit Margin: {h['profit_margin']:.1f}%  [{h.get('sector','-')}]"
            )
        point(point_num, f"Highest Profit Margins (Latest Quarter):\n" + "\n".join(margin_lines))

    # 8. News Highlights
    section("KEY NEWS & MARKET EVENTS")
    news = get_recent_news_summary(store, limit=10)
    market_news = get_market_news(store, limit=5)
    all_news = market_news + news
    if all_news:
        point_num += 1
        news_lines = []
        seen_titles: set[str] = set()
        for n in all_news:
            title = n.get("title", "")
            if title in seen_titles or not title:
                continue
            seen_titles.add(title)
            sym = n.get("symbol", "")
            src = n.get("source_name", "")
            news_lines.append(f"      [{sym}] {title[:80]}  ({src})")
            if len(news_lines) >= 8:
                break
        point(point_num, f"Recent Headlines:\n" + "\n".join(news_lines))

    # 9. Quick sector investment notes
    section("WHERE TO LOOK")
    if perf_30d:
        point_num += 1
        notes: list[str] = []

        # Find sectors with strong momentum + good breadth
        for s in perf_30d[:3]:
            gainers_count = sum(1 for st in s.get("top_gainers", []) if st.get("change_pct", 0) > 0)
            if s["avg_change_pct"] > 2:
                notes.append(f"      - {s['sector']}: Strong momentum ({'+' if s['avg_change_pct']>0 else ''}{s['avg_change_pct']:.1f}% avg). "
                           f"Broad-based rally across {s['stock_count']} stocks.")
            elif s["avg_change_pct"] > 0:
                notes.append(f"      - {s['sector']}: Modest gains ({'+' if s['avg_change_pct']>0 else ''}{s['avg_change_pct']:.1f}% avg). "
                           f"Selective opportunities in {s['stock_count']} stocks.")

        # Find beaten-down sectors that might be reversing
        for s in perf_30d[-3:]:
            if s["avg_change_pct"] < -5:
                notes.append(f"      - {s['sector']}: Heavily beaten down ({s['avg_change_pct']:.1f}% avg). "
                           f"Potential value play — watch for reversal signals.")

        if notes:
            point(point_num, f"Sector Investment Notes:\n" + "\n".join(notes))

    # Summary line
    lines.append(f"\n{'='*60}")
    lines.append(f"  Total insights: {point_num} | Data coverage: {breadth_30d.get('total', 0)} stocks")
    lines.append(f"  Run 'main.py news' to refresh news data for latest headlines")
    lines.append(f"{'='*60}\n")

    return "\n".join(lines)


def run(store: DataStore) -> str:
    """Generate and print the market intelligence report."""
    # Check data readiness
    counts = store.get_table_counts()
    if counts.get("stocks", 0) == 0:
        return "Error: No stocks in database. Run 'main.py list' first."
    if counts.get("prices", 0) == 0:
        return "Error: No price data. Run 'main.py prices' first."

    # Check sector coverage
    row = store.conn.execute("SELECT COUNT(*) as cnt FROM stocks WHERE sector IS NOT NULL").fetchone()
    sector_count = row["cnt"] if row else 0
    if sector_count < 50:
        logger.warning(
            f"Only {sector_count} stocks have sector data. "
            f"Run 'main.py list' (without --skip-enrichment) for full sector mapping."
        )

    report = generate_report(store)
    print(report)
    return report


if __name__ == "__main__":
    store = DataStore()
    try:
        run(store)
    finally:
        store.close()
