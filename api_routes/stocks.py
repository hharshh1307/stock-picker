"""Stocks API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from embedding_search import semantic_search

router = APIRouter()

def _get_store():
    from api_server import get_store
    return get_store()


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query (symbol or company name)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results")
) -> list[dict[str, Any]]:
    """Search stocks using hybrid SQL + semantic search."""
    store = _get_store()
    stocks = semantic_search(q, limit=limit)

    if not stocks:
        return []

    # Fetch latest price + previous day close for each symbol in one query
    symbols = [s.symbol for s in stocks]
    placeholders = ",".join("?" * len(symbols))
    price_rows = store.conn.execute(
        f"""
        SELECT p.symbol,
               p.close                                           AS latest_price,
               p.date                                            AS price_date,
               prev.close                                        AS prev_close
        FROM prices p
        INNER JOIN (
            SELECT symbol, MAX(date) AS max_date FROM prices
            WHERE symbol IN ({placeholders})
            GROUP BY symbol
        ) latest ON p.symbol = latest.symbol AND p.date = latest.max_date
        LEFT JOIN prices prev
               ON prev.symbol = p.symbol
              AND prev.date = (
                    SELECT MAX(date) FROM prices
                    WHERE symbol = p.symbol AND date < p.date
              )
        """,
        symbols,
    ).fetchall()

    price_map = {}
    for r in price_rows:
        change = None
        if r["prev_close"] and r["prev_close"] > 0:
            change = round(((r["latest_price"] - r["prev_close"]) / r["prev_close"]) * 100, 2)
        price_map[r["symbol"]] = {
            "latest_price": r["latest_price"],
            "change_1d_pct": change,
        }

    return [
        {
            "symbol":        s.symbol,
            "company_name":  s.company_name,
            "sector":        s.sector,
            "industry":      s.industry,
            "latest_price":  price_map.get(s.symbol, {}).get("latest_price"),
            "change_1d_pct": price_map.get(s.symbol, {}).get("change_1d_pct"),
        }
        for s in stocks
    ]


@router.get("/{symbol}")
async def stock_detail(symbol: str) -> dict[str, Any]:
    """Get comprehensive stock detail."""
    store = _get_store()
    detail = store.get_stock_detail(symbol.upper())

    if not detail:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    # Add sparkline data
    from discovery_engine import _get_sparkline_data
    detail["sparkline_data"] = _get_sparkline_data(store, symbol.upper(), days=30)

    return detail


@router.get("/{symbol}/prices")
async def stock_prices(
    symbol: str,
    days: int = Query(default=365, ge=1, le=730, description="Number of days of history")
) -> list[dict[str, Any]]:
    """Get price series for charting."""
    store = _get_store()

    # Verify stock exists
    stock = store.get_stock(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    return store.get_price_series(symbol.upper(), days=days)


@router.get("/{symbol}/financials")
async def stock_financials(symbol: str) -> list[dict[str, Any]]:
    """Get quarterly financial summary."""
    store = _get_store()

    # Verify stock exists
    stock = store.get_stock(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    return store.get_financials_summary(symbol.upper())


@router.get("/{symbol}/news")
async def stock_news(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum news items")
) -> list[dict[str, Any]]:
    """Get news for a specific stock."""
    store = _get_store()

    # Verify stock exists
    stock = store.get_stock(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    return store.get_stock_news(symbol.upper(), limit=limit)


@router.get("/")
async def list_stocks(
    sector: str = Query(default=None, description="Filter by sector"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum results")
) -> list[dict[str, Any]]:
    """List all stocks, optionally filtered by sector."""
    store = _get_store()

    if sector:
        stocks = store.get_stocks_by_sector(sector)
    else:
        stocks = store.get_all_stocks()

    return [
        {
            "symbol": s.symbol,
            "company_name": s.company_name,
            "sector": s.sector,
            "industry": s.industry,
        }
        for s in stocks[:limit]
    ]
