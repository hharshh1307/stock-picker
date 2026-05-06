from datetime import datetime, date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from data_store import DataStore
from models import UserProfile, InvestmentPlan, PortfolioItem

router = APIRouter()

def _get_store():
    from api_server import get_store
    return get_store()

# --- Pydantic Models for Input ---

class UserProfileInput(BaseModel):
    risk_tolerance: str
    total_capital: float
    expected_returns: float

class InvestmentPlanInput(BaseModel):
    id: int | None = None
    frequency: str
    allocated_amount: float
    description: str | None = None

class PortfolioItemInput(BaseModel):
    id: int | None = None
    symbol: str
    quantity: float
    average_buy_price: float
    strategy_frequency: str | None = None


# --- Helpers ---

def _enrich_holding_with_pnl(store: DataStore, symbol: str, quantity: float, avg_price: float) -> dict:
    """
    Look up the latest close price and 30-day-ago price for a symbol
    from the local price DB and compute unrealized P&L metrics.
    """
    # Latest price
    latest_row = store.conn.execute(
        "SELECT close, date FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
        (symbol,),
    ).fetchone()

    latest_price: float | None = float(latest_row["close"]) if latest_row else None
    price_date: str | None = latest_row["date"] if latest_row else None

    # Price 30 days ago
    cutoff_30d = (date.today() - timedelta(days=30)).isoformat()
    row_30d = store.conn.execute(
        "SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1",
        (symbol, cutoff_30d),
    ).fetchone()
    price_30d_ago: float | None = float(row_30d["close"]) if row_30d else None

    # Price 365 days ago (52w low/high)
    cutoff_52w = (date.today() - timedelta(days=365)).isoformat()
    row_52w = store.conn.execute(
        "SELECT MIN(low) as low_52w, MAX(high) as high_52w FROM prices WHERE symbol = ? AND date >= ?",
        (symbol, cutoff_52w),
    ).fetchone()

    # Stock metadata
    stock = store.get_stock(symbol)

    invested_value = round(quantity * avg_price, 2)
    current_value = round(quantity * latest_price, 2) if latest_price else None
    unrealized_pnl = round(current_value - invested_value, 2) if current_value is not None else None
    pnl_pct = round((unrealized_pnl / invested_value) * 100, 2) if unrealized_pnl is not None and invested_value > 0 else None
    change_30d = None
    if latest_price and price_30d_ago and price_30d_ago > 0:
        change_30d = round(((latest_price - price_30d_ago) / price_30d_ago) * 100, 2)

    return {
        "invested_value": invested_value,
        "current_value": current_value,
        "latest_price": latest_price,
        "price_date": price_date,
        "unrealized_pnl": unrealized_pnl,
        "pnl_pct": pnl_pct,
        "change_30d_pct": change_30d,
        "high_52w": float(row_52w["high_52w"]) if row_52w and row_52w["high_52w"] else None,
        "low_52w": float(row_52w["low_52w"]) if row_52w and row_52w["low_52w"] else None,
        "company_name": stock.company_name if stock else symbol,
        "sector": stock.sector if stock else None,
    }


# --- Profile Endpoints ---

@router.get("/profile")
async def get_profile(store: DataStore = Depends(_get_store)) -> Any:
    profile = store.get_user_profile()
    if not profile:
        return {"risk_tolerance": "medium", "total_capital": 0, "expected_returns": 0}
    return profile

@router.post("/profile")
async def update_profile(profile: UserProfileInput, store: DataStore = Depends(_get_store)) -> Any:
    p = UserProfile(
        id=None,
        risk_tolerance=profile.risk_tolerance,
        total_capital=profile.total_capital,
        expected_returns=profile.expected_returns
    )
    store.upsert_user_profile(p)
    return {"status": "success"}


# --- Plans Endpoints ---

@router.get("/plans")
async def get_plans(store: DataStore = Depends(_get_store)) -> Any:
    return store.get_investment_plans()

@router.post("/plans")
async def upsert_plan(plan: InvestmentPlanInput, store: DataStore = Depends(_get_store)) -> Any:
    p = InvestmentPlan(
        id=plan.id,
        frequency=plan.frequency,
        allocated_amount=plan.allocated_amount,
        description=plan.description
    )
    store.upsert_investment_plan(p)
    return {"status": "success"}

@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int, store: DataStore = Depends(_get_store)) -> Any:
    store.delete_investment_plan(plan_id)
    return {"status": "success"}


# --- Portfolio Endpoints ---

@router.get("/portfolio")
async def get_portfolio(store: DataStore = Depends(_get_store)) -> Any:
    """Returns the raw portfolio items. Use /portfolio/pnl for enriched P&L data."""
    from groww_integration import fetch_live_groww_portfolio, save_live_portfolio_to_cache

    live_result = fetch_live_groww_portfolio()
    if live_result.get("status") == "success":
        save_live_portfolio_to_cache(live_result["structured_portfolio"])
        live_items = []
        for i, item in enumerate(live_result["structured_portfolio"]):
            live_items.append({
                "id": 1000 + i,
                "symbol": item["asset_name"],
                "quantity": item["quantity"],
                "average_buy_price": item["rate"],
                "strategy_frequency": "Long-term",
                "added_at": datetime.now().isoformat(),
                "is_live_synced": True,
            })
        return live_items

    return store.get_portfolio_items()


@router.get("/portfolio/pnl")
async def get_portfolio_pnl(store: DataStore = Depends(_get_store)) -> Any:
    """
    Returns enriched portfolio with real-time P&L computed by cross-referencing:
    - Groww live holdings (or local DB fallback) for quantity + average buy price
    - Local price DB for latest close price, 30d change, 52w range
    """
    from groww_integration import fetch_live_groww_portfolio, save_live_portfolio_to_cache

    # ── Source: Groww live or local DB ──────────────────────────────────────
    raw_holdings: list[dict] = []
    source = "local_db"
    available_cash: float | None = None
    account_info: dict = {}

    live_result = fetch_live_groww_portfolio()
    if live_result.get("status") == "success":
        save_live_portfolio_to_cache(live_result["structured_portfolio"])
        raw_holdings = live_result["structured_portfolio"]
        available_cash = live_result.get("available_cash")
        account_info = live_result.get("user_profile", {})
        source = "live_groww_api"
    else:
        # Fallback: local DB holdings
        db_items = store.get_portfolio_items()
        raw_holdings = [
            {
                "asset_name": item.symbol,
                "quantity": item.quantity,
                "rate": item.average_buy_price,
                "strategy_frequency": item.strategy_frequency,
            }
            for item in db_items
        ]

    # ── Enrich each holding with local price P&L ─────────────────────────
    holdings = []
    total_invested = 0.0
    total_current = 0.0
    total_pnl = 0.0
    has_current_prices = False

    for item in raw_holdings:
        symbol: str = item.get("asset_name") or item.get("symbol") or ""
        quantity: float = float(item.get("quantity", 0))
        avg_price: float = float(item.get("rate", item.get("average_buy_price", 0)))

        pnl_data = _enrich_holding_with_pnl(store, symbol, quantity, avg_price)

        holding = {
            "symbol": symbol,
            "company_name": pnl_data["company_name"],
            "sector": pnl_data["sector"],
            "quantity": quantity,
            "average_buy_price": avg_price,
            "strategy_frequency": item.get("strategy_frequency", "Long-term"),
            # Price data
            "latest_price": pnl_data["latest_price"],
            "price_date": pnl_data["price_date"],
            "high_52w": pnl_data["high_52w"],
            "low_52w": pnl_data["low_52w"],
            # P&L
            "invested_value": pnl_data["invested_value"],
            "current_value": pnl_data["current_value"],
            "unrealized_pnl": pnl_data["unrealized_pnl"],
            "pnl_pct": pnl_data["pnl_pct"],
            "change_30d_pct": pnl_data["change_30d_pct"],
            # Groww-specific extras
            "isin": item.get("isin"),
            "t1_quantity": item.get("t1_quantity"),
            "demat_free_quantity": item.get("demat_free_quantity"),
            "is_live_synced": source == "live_groww_api",
        }

        total_invested += pnl_data["invested_value"]
        if pnl_data["current_value"] is not None:
            total_current += pnl_data["current_value"]
            total_pnl += pnl_data["unrealized_pnl"] or 0
            has_current_prices = True

        holdings.append(holding)

    total_pnl_pct = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 and has_current_prices else None

    return {
        "source": source,
        "account_info": {
            "ucc": account_info.get("ucc"),
            "active_segments": account_info.get("active_segments", []),
            "ddpi_enabled": account_info.get("ddpi_enabled"),
        } if account_info else None,
        "available_cash": available_cash,
        "summary": {
            "holding_count": len(holdings),
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2) if has_current_prices else None,
            "total_unrealized_pnl": round(total_pnl, 2) if has_current_prices else None,
            "total_pnl_pct": total_pnl_pct,
        },
        "holdings": holdings,
    }


@router.post("/portfolio")
async def upsert_portfolio_item(item: PortfolioItemInput, store: DataStore = Depends(_get_store)) -> Any:
    p = PortfolioItem(
        id=item.id,
        symbol=item.symbol.upper(),
        quantity=item.quantity,
        average_buy_price=item.average_buy_price,
        strategy_frequency=item.strategy_frequency,
        added_at=datetime.now()
    )
    store.upsert_portfolio_item(p)
    return {"status": "success"}

@router.delete("/portfolio/{item_id}")
async def delete_portfolio_item(item_id: int, store: DataStore = Depends(_get_store)) -> Any:
    store.delete_portfolio_item(item_id)
    return {"status": "success"}

