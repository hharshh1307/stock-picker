"""Discovery Engine — Computes 8 stock discovery buckets from local data.

All buckets are computed from existing SQLite data (prices, stocks, quarterly_financials).
No external API calls needed.
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from data_store import DataStore
from market_intelligence import (
    get_market_breadth,
    get_sector_performance,
    get_top_movers,
    get_volume_spikes,
)

# ── Request-scoped cache: avoids re-running expensive queries multiple times ──
# Keyed by (id(store), days) so it resets naturally per server request.
_price_change_cache: dict = {}


@dataclass
class BucketStock:
    """A stock entry within a discovery bucket."""
    symbol: str
    company_name: str
    sector: Optional[str]
    industry: Optional[str]
    metric_value: float
    metric_label: str
    latest_price: float
    change_pct: float
    sparkline_data: list[float]  # Last 30 daily close prices


@dataclass
class Bucket:
    """A discovery bucket containing stocks matching specific criteria."""
    bucket_id: str
    name: str
    description: str
    stocks: list[BucketStock]


def _get_sparkline_data(store: DataStore, symbol: str, days: int = 30) -> list[float]:
    """Get the last N days of close prices for sparkline chart."""
    cutoff = (date.today() - timedelta(days=days + 10)).isoformat()
    rows = store.conn.execute(
        """SELECT close FROM prices
           WHERE symbol = ? AND date >= ?
           ORDER BY date ASC
           LIMIT ?""",
        (symbol, cutoff, days),
    ).fetchall()
    return [r["close"] for r in rows]


def _get_sparklines_batch(store: DataStore, symbols: list[str], days: int = 30) -> dict[str, list[float]]:
    """Fetch sparklines for multiple symbols in ONE SQL query."""
    if not symbols:
        return {}
    cutoff = (date.today() - timedelta(days=days + 10)).isoformat()
    placeholders = ",".join("?" * len(symbols))
    rows = store.conn.execute(
        f"""SELECT symbol, close, date FROM prices
            WHERE symbol IN ({placeholders}) AND date >= ?
            ORDER BY symbol, date ASC""",
        symbols + [cutoff],
    ).fetchall()
    result: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        result[r["symbol"]].append(r["close"])
    # Trim to last `days` values
    return {s: v[-days:] for s, v in result.items()}


def _get_latest_prices(store: DataStore, symbols: list[str]) -> dict[str, tuple[float, str]]:
    """Get latest price and date for multiple symbols. Returns {symbol: (price, date)}."""
    if not symbols:
        return {}
    placeholders = ",".join("?" * len(symbols))
    rows = store.conn.execute(
        f"""SELECT symbol, close, date FROM prices
            WHERE (symbol, date) IN (
                SELECT symbol, MAX(date) FROM prices
                WHERE symbol IN ({placeholders})
                GROUP BY symbol
            )""",
        symbols,
    ).fetchall()
    return {r["symbol"]: (r["close"], r["date"]) for r in rows}


def _get_price_changes(store: DataStore, days: int = 30) -> list[dict]:
    """Get price change % for all stocks over the last N days.
    Results are cached per (store_id, days) to avoid re-running across multiple buckets.
    """
    cache_key = (id(store), days)
    if cache_key in _price_change_cache:
        return _price_change_cache[cache_key]

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = store.conn.execute(
        """
        WITH price_range AS (
            SELECT p.symbol, s.company_name, s.sector, s.industry,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date ASC) as start_price,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as end_price
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
        )
        SELECT DISTINCT symbol, company_name, sector, industry, start_price, end_price,
               CASE WHEN start_price > 0 THEN ((end_price - start_price) / start_price) * 100 ELSE 0 END as change_pct
        FROM price_range
        WHERE start_price > 0
        """,
        (cutoff,),
    ).fetchall()
    result = [dict(r) for r in rows]
    _price_change_cache[cache_key] = result
    return result


def _clear_price_cache():
    """Call at the start of get_all_buckets to reset the per-request cache."""
    _price_change_cache.clear()


def get_momentum_leaders(store: DataStore, limit: int = 15) -> Bucket:
    """Top stocks by 30-day price change %."""
    changes = _get_price_changes(store, days=30)
    changes.sort(key=lambda x: x["change_pct"], reverse=True)
    top = changes[:limit]

    sparklines = _get_sparklines_batch(store, [s["symbol"] for s in top])
    stocks = []
    for s in top:
        stocks.append(BucketStock(
            symbol=s["symbol"],
            company_name=s["company_name"],
            sector=s["sector"],
            industry=s["industry"],
            metric_value=round(s["change_pct"], 2),
            metric_label="30D Change",
            latest_price=s["end_price"],
            change_pct=round(s["change_pct"], 2),
            sparkline_data=sparklines.get(s["symbol"], []),
        ))

    return Bucket(
        bucket_id="momentum_leaders",
        name="Momentum Leaders",
        description="Top performing stocks over the last 30 days",
        stocks=stocks,
    )


def get_beaten_down(store: DataStore, limit: int = 15) -> Bucket:
    """Bottom stocks by 30-day price change %."""
    changes = _get_price_changes(store, days=30)
    changes.sort(key=lambda x: x["change_pct"])
    bottom = changes[:limit]

    sparklines = _get_sparklines_batch(store, [s["symbol"] for s in bottom])
    stocks = []
    for s in bottom:
        stocks.append(BucketStock(
            symbol=s["symbol"],
            company_name=s["company_name"],
            sector=s["sector"],
            industry=s["industry"],
            metric_value=round(s["change_pct"], 2),
            metric_label="30D Change",
            latest_price=s["end_price"],
            change_pct=round(s["change_pct"], 2),
            sparkline_data=sparklines.get(s["symbol"], []),
        ))

    return Bucket(
        bucket_id="beaten_down",
        name="Beaten Down",
        description="Stocks that have fallen the most in 30 days — potential value plays",
        stocks=stocks,
    )


def get_volume_surge_bucket(store: DataStore, limit: int = 15) -> Bucket:
    """Stocks with recent volume significantly above average."""
    spikes = get_volume_spikes(store, days=5, threshold=1.5)[:limit]

    # Get price data for these stocks
    symbols = [s["symbol"] for s in spikes]
    latest_prices = _get_latest_prices(store, symbols)
    changes = {s["symbol"]: s for s in _get_price_changes(store, days=30)}

    sparklines = _get_sparklines_batch(store, [s["symbol"] for s in spikes[:limit]])
    stocks = []
    for s in spikes:
        symbol = s["symbol"]
        price_info = latest_prices.get(symbol, (0, ""))
        change_info = changes.get(symbol, {})

        stocks.append(BucketStock(
            symbol=symbol,
            company_name=s.get("company_name", symbol),
            sector=s.get("sector"),
            industry=None,
            metric_value=round(s.get("vol_ratio", 0), 1),
            metric_label="Volume Ratio",
            latest_price=price_info[0],
            change_pct=round(change_info.get("change_pct", 0), 2),
            sparkline_data=sparklines.get(symbol, []),
        ))

    return Bucket(
        bucket_id="volume_surge",
        name="Volume Surge",
        description="Unusual trading activity — volume 1.5x+ above 60-day average",
        stocks=stocks,
    )


def get_revenue_rockets(store: DataStore, limit: int = 15) -> Bucket:
    """Top stocks by quarter-over-quarter revenue growth."""
    # Get latest 2 quarters per stock for comparison
    rows = store.conn.execute(
        """SELECT symbol, period_ending, data_json
           FROM quarterly_financials
           WHERE statement_type = 'income'
           ORDER BY symbol, period_ending DESC"""
    ).fetchall()

    stock_quarters: dict[str, list] = defaultdict(list)
    for r in rows:
        if len(stock_quarters[r["symbol"]]) < 2:
            stock_quarters[r["symbol"]].append({
                "period": r["period_ending"],
                "data": json.loads(r["data_json"]),
            })

    growth_data = []
    for symbol, quarters in stock_quarters.items():
        if len(quarters) < 2:
            continue
        latest = quarters[0]["data"]
        prev = quarters[1]["data"]

        revenue = latest.get("Total Revenue") or latest.get("Operating Revenue")
        prev_revenue = prev.get("Total Revenue") or prev.get("Operating Revenue")

        if not revenue or not prev_revenue or prev_revenue <= 0:
            continue

        growth = ((revenue - prev_revenue) / prev_revenue) * 100
        if abs(growth) > 500:  # Filter extreme outliers
            continue

        growth_data.append({
            "symbol": symbol,
            "revenue_growth": growth,
            "revenue": revenue,
        })

    growth_data.sort(key=lambda x: x["revenue_growth"], reverse=True)
    top = growth_data[:limit]

    # Get stock info and price data
    symbols = [g["symbol"] for g in top]
    latest_prices = _get_latest_prices(store, symbols)
    changes = {s["symbol"]: s for s in _get_price_changes(store, days=30)}

    sparklines = _get_sparklines_batch(store, [g["symbol"] for g in top])
    stocks = []
    for g in top:
        symbol = g["symbol"]
        stock = store.get_stock(symbol)
        price_info = latest_prices.get(symbol, (0, ""))
        change_info = changes.get(symbol, {})

        stocks.append(BucketStock(
            symbol=symbol,
            company_name=stock.company_name if stock else symbol,
            sector=stock.sector if stock else None,
            industry=stock.industry if stock else None,
            metric_value=round(g["revenue_growth"], 1),
            metric_label="QoQ Revenue Growth",
            latest_price=price_info[0],
            change_pct=round(change_info.get("change_pct", 0), 2),
            sparkline_data=sparklines.get(symbol, []),
        ))

    return Bucket(
        bucket_id="revenue_rockets",
        name="Revenue Rockets",
        description="Fastest growing companies by quarterly revenue",
        stocks=stocks,
    )


def get_profit_machines(store: DataStore, limit: int = 15) -> Bucket:
    """Top stocks by profit margin (latest quarter)."""
    rows = store.conn.execute(
        """SELECT qf.symbol, qf.data_json, s.company_name, s.sector, s.industry
           FROM quarterly_financials qf
           JOIN stocks s ON qf.symbol = s.symbol
           WHERE qf.statement_type = 'income'
             AND qf.period_ending = (
                 SELECT MAX(period_ending) FROM quarterly_financials
                 WHERE symbol = qf.symbol AND statement_type = 'income'
             )"""
    ).fetchall()

    margin_data = []
    for r in rows:
        data = json.loads(r["data_json"])
        revenue = data.get("Total Revenue") or data.get("Operating Revenue")
        net_income = data.get("Net Income") or data.get("Net Income From Continuing Operation Net Minority Interest")

        if not revenue or not net_income or revenue <= 0:
            continue

        margin = (net_income / revenue) * 100
        if abs(margin) > 100:  # Filter outliers
            continue

        margin_data.append({
            "symbol": r["symbol"],
            "company_name": r["company_name"],
            "sector": r["sector"],
            "industry": r["industry"],
            "profit_margin": margin,
        })

    margin_data.sort(key=lambda x: x["profit_margin"], reverse=True)
    top = margin_data[:limit]

    # Get price data
    symbols = [m["symbol"] for m in top]
    latest_prices = _get_latest_prices(store, symbols)
    changes = {s["symbol"]: s for s in _get_price_changes(store, days=30)}

    sparklines = _get_sparklines_batch(store, [m["symbol"] for m in top])
    stocks = []
    for m in top:
        symbol = m["symbol"]
        price_info = latest_prices.get(symbol, (0, ""))
        change_info = changes.get(symbol, {})

        stocks.append(BucketStock(
            symbol=symbol,
            company_name=m["company_name"],
            sector=m["sector"],
            industry=m["industry"],
            metric_value=round(m["profit_margin"], 1),
            metric_label="Profit Margin %",
            latest_price=price_info[0],
            change_pct=round(change_info.get("change_pct", 0), 2),
            sparkline_data=sparklines.get(symbol, []),
        ))

    return Bucket(
        bucket_id="profit_machines",
        name="Profit Machines",
        description="Highest profit margin companies (latest quarter)",
        stocks=stocks,
    )


def get_near_52w_high(store: DataStore, limit: int = 15) -> Bucket:
    """Stocks trading within 5% of their 52-week high."""
    cutoff_52w = (date.today() - timedelta(days=365)).isoformat()

    rows = store.conn.execute(
        """
        WITH price_stats AS (
            SELECT p.symbol, s.company_name, s.sector, s.industry,
                   MAX(p.high) as high_52w,
                   (SELECT close FROM prices WHERE symbol = p.symbol ORDER BY date DESC LIMIT 1) as latest_close
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
            GROUP BY p.symbol
        )
        SELECT *,
               ((high_52w - latest_close) / high_52w * 100) as pct_from_high
        FROM price_stats
        WHERE high_52w > 0 AND latest_close > 0
          AND ((high_52w - latest_close) / high_52w * 100) <= 5
        ORDER BY pct_from_high ASC
        LIMIT ?
        """,
        (cutoff_52w, limit),
    ).fetchall()

    changes = {s["symbol"]: s for s in _get_price_changes(store, days=30)}

    sparklines = _get_sparklines_batch(store, [r["symbol"] for r in rows])
    stocks = []
    for r in rows:
        symbol = r["symbol"]
        change_info = changes.get(symbol, {})

        stocks.append(BucketStock(
            symbol=symbol,
            company_name=r["company_name"],
            sector=r["sector"],
            industry=r["industry"],
            metric_value=round(r["pct_from_high"], 1),
            metric_label="% from 52W High",
            latest_price=r["latest_close"],
            change_pct=round(change_info.get("change_pct", 0), 2),
            sparkline_data=sparklines.get(symbol, []),
        ))

    return Bucket(
        bucket_id="near_52w_high",
        name="Near 52-Week High",
        description="Stocks trading within 5% of their yearly high — showing strength",
        stocks=stocks,
    )


def get_near_52w_low(store: DataStore, limit: int = 15) -> Bucket:
    """Stocks trading within 5% of their 52-week low."""
    cutoff_52w = (date.today() - timedelta(days=365)).isoformat()

    rows = store.conn.execute(
        """
        WITH price_stats AS (
            SELECT p.symbol, s.company_name, s.sector, s.industry,
                   MIN(p.low) as low_52w,
                   (SELECT close FROM prices WHERE symbol = p.symbol ORDER BY date DESC LIMIT 1) as latest_close
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
            GROUP BY p.symbol
        )
        SELECT *,
               ((latest_close - low_52w) / low_52w * 100) as pct_from_low
        FROM price_stats
        WHERE low_52w > 0 AND latest_close > 0
          AND ((latest_close - low_52w) / low_52w * 100) <= 5
        ORDER BY pct_from_low ASC
        LIMIT ?
        """,
        (cutoff_52w, limit),
    ).fetchall()

    changes = {s["symbol"]: s for s in _get_price_changes(store, days=30)}

    sparklines = _get_sparklines_batch(store, [r["symbol"] for r in rows])
    stocks = []
    for r in rows:
        symbol = r["symbol"]
        change_info = changes.get(symbol, {})

        stocks.append(BucketStock(
            symbol=symbol,
            company_name=r["company_name"],
            sector=r["sector"],
            industry=r["industry"],
            metric_value=round(r["pct_from_low"], 1),
            metric_label="% from 52W Low",
            latest_price=r["latest_close"],
            change_pct=round(change_info.get("change_pct", 0), 2),
            sparkline_data=sparklines.get(symbol, []),
        ))

    return Bucket(
        bucket_id="near_52w_low",
        name="Near 52-Week Low",
        description="Stocks near their yearly low — potential value or falling knives",
        stocks=stocks,
    )


def get_sector_outperformers(store: DataStore, top_per_sector: int = 3) -> Bucket:
    """Top stocks from each sector that beat their sector average."""
    sector_perf = get_sector_performance(store, days=30)
    sector_avg = {s["sector"]: s["avg_change_pct"] for s in sector_perf}

    changes = _get_price_changes(store, days=30)

    # Group by sector and find outperformers
    by_sector: dict[str, list] = defaultdict(list)
    for s in changes:
        if s["sector"] and s["sector"] in sector_avg:
            sector_mean = sector_avg[s["sector"]]
            if s["change_pct"] > sector_mean:
                s["outperformance"] = s["change_pct"] - sector_mean
                by_sector[s["sector"]].append(s)

    # Get top N from each sector
    sector_symbols = []
    for sector, sector_stocks in by_sector.items():
        sector_stocks.sort(key=lambda x: x["outperformance"], reverse=True)
        sector_symbols.extend([s["symbol"] for s in sector_stocks[:top_per_sector]])

    sparklines = _get_sparklines_batch(store, sector_symbols)
    stocks = []
    for sector, sector_stocks in by_sector.items():
        sector_stocks.sort(key=lambda x: x["outperformance"], reverse=True)
        for s in sector_stocks[:top_per_sector]:
            stocks.append(BucketStock(
                symbol=s["symbol"],
                company_name=s["company_name"],
                sector=s["sector"],
                industry=s["industry"],
                metric_value=round(s["outperformance"], 1),
                metric_label="vs Sector Avg",
                latest_price=s["end_price"],
                change_pct=round(s["change_pct"], 2),
                sparkline_data=sparklines.get(s["symbol"], []),
            ))

    # Sort by outperformance overall
    stocks.sort(key=lambda x: x.metric_value, reverse=True)

    return Bucket(
        bucket_id="sector_outperformers",
        name="Sector Outperformers",
        description="Top stocks beating their sector average — relative strength leaders",
        stocks=stocks,
    )


def get_all_buckets(store: DataStore) -> list[Bucket]:
    """Get all 8 discovery buckets. Uses cached price changes for efficiency."""
    _clear_price_cache()  # Reset per-request cache
    return [
        get_momentum_leaders(store),
        get_beaten_down(store),
        get_volume_surge_bucket(store),
        get_revenue_rockets(store),
        get_profit_machines(store),
        get_near_52w_high(store),
        get_near_52w_low(store),
        get_sector_outperformers(store),
    ]


def get_bucket_by_id(store: DataStore, bucket_id: str, limit: int = 50) -> Optional[Bucket]:
    """Get a specific bucket by ID with optional limit."""
    bucket_funcs = {
        "momentum_leaders": lambda: get_momentum_leaders(store, limit=limit),
        "beaten_down": lambda: get_beaten_down(store, limit=limit),
        "volume_surge": lambda: get_volume_surge_bucket(store, limit=limit),
        "revenue_rockets": lambda: get_revenue_rockets(store, limit=limit),
        "profit_machines": lambda: get_profit_machines(store, limit=limit),
        "near_52w_high": lambda: get_near_52w_high(store, limit=limit),
        "near_52w_low": lambda: get_near_52w_low(store, limit=limit),
        "sector_outperformers": lambda: get_sector_outperformers(store),
    }
    if bucket_id in bucket_funcs:
        return bucket_funcs[bucket_id]()
    return None


def get_market_pulse(store: DataStore) -> dict:
    """Get market pulse data: breadth, index change, sentiment."""
    breadth = get_market_breadth(store, days=30)
    breadth_7d = get_market_breadth(store, days=7)

    # Get Nifty 500 index change
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    index_data = store.conn.execute(
        """SELECT
               FIRST_VALUE(close) OVER (ORDER BY date ASC) as start_close,
               FIRST_VALUE(close) OVER (ORDER BY date DESC) as end_close
           FROM index_data
           WHERE date >= ? AND index_name = 'Nifty 500'
           LIMIT 1""",
        (cutoff,),
    ).fetchone()

    index_change = 0.0
    if index_data and index_data["start_close"] and index_data["start_close"] > 0:
        index_change = ((index_data["end_close"] - index_data["start_close"]) / index_data["start_close"]) * 100

    # Determine sentiment
    if breadth["breadth_ratio"] > 1.5:
        sentiment = "STRONGLY_BULLISH"
    elif breadth["breadth_ratio"] > 1.2:
        sentiment = "BULLISH"
    elif breadth["breadth_ratio"] < 0.67:
        sentiment = "STRONGLY_BEARISH"
    elif breadth["breadth_ratio"] < 0.83:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    return {
        "sentiment": sentiment,
        "breadth_ratio_30d": breadth["breadth_ratio"],
        "breadth_ratio_7d": breadth_7d["breadth_ratio"],
        "advancing_30d": breadth["advancing"],
        "declining_30d": breadth["declining"],
        "advancing_7d": breadth_7d["advancing"],
        "declining_7d": breadth_7d["declining"],
        "total_stocks": breadth["total"],
        "index_change_30d": round(index_change, 2),
    }


def get_sectors_summary(store: DataStore) -> list[dict]:
    """Get sector summary for the sector grid."""
    sector_perf = get_sector_performance(store, days=30)

    result = []
    for s in sector_perf:
        top_gainer = s["top_gainers"][0] if s["top_gainers"] else None
        result.append({
            "sector": s["sector"],
            "avg_return": s["avg_change_pct"],
            "stock_count": s["stock_count"],
            "top_stock": top_gainer["symbol"] if top_gainer else None,
            "top_stock_return": top_gainer["change_pct"] if top_gainer else None,
        })

    return result


def get_movers_summary(store: DataStore, limit: int = 10) -> dict:
    """Get top movers for the movers table."""
    movers = get_top_movers(store, days=30, limit=limit)

    # Get sparkline data for movers
    gainers = []
    for g in movers.get("gainers", []):
        sparkline = _get_sparkline_data(store, g["symbol"])
        gainers.append({
            **g,
            "sparkline_data": sparkline,
        })

    losers = []
    for l in movers.get("losers", []):
        sparkline = _get_sparkline_data(store, l["symbol"])
        losers.append({
            **l,
            "sparkline_data": sparkline,
        })

    return {
        "gainers": gainers,
        "losers": losers,
    }
