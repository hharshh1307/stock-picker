"""Stocks API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api_server import get_store

router = APIRouter()


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query (symbol or company name)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results")
) -> list[dict[str, Any]]:
    """Search stocks by symbol or company name."""
    store = get_store()
    stocks = store.search_stocks(q, limit=limit)

    return [
        {
            "symbol": s.symbol,
            "company_name": s.company_name,
            "sector": s.sector,
            "industry": s.industry,
        }
        for s in stocks
    ]


@router.get("/{symbol}")
async def stock_detail(symbol: str) -> dict[str, Any]:
    """Get comprehensive stock detail."""
    store = get_store()
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
    store = get_store()

    # Verify stock exists
    stock = store.get_stock(symbol.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    return store.get_price_series(symbol.upper(), days=days)


@router.get("/{symbol}/financials")
async def stock_financials(symbol: str) -> list[dict[str, Any]]:
    """Get quarterly financial summary."""
    store = get_store()

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
    store = get_store()

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
    store = get_store()

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
