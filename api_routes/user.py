from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api_server import get_store
from data_store import DataStore
from models import UserProfile, InvestmentPlan, PortfolioItem

router = APIRouter()

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


# --- Profile Endpoints ---

@router.get("/profile")
async def get_profile(store: DataStore = Depends(get_store)) -> Any:
    profile = store.get_user_profile()
    if not profile:
        return {"risk_tolerance": "medium", "total_capital": 0, "expected_returns": 0}
    return profile

@router.post("/profile")
async def update_profile(profile: UserProfileInput, store: DataStore = Depends(get_store)) -> Any:
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
async def get_plans(store: DataStore = Depends(get_store)) -> Any:
    return store.get_investment_plans()

@router.post("/plans")
async def upsert_plan(plan: InvestmentPlanInput, store: DataStore = Depends(get_store)) -> Any:
    p = InvestmentPlan(
        id=plan.id,
        frequency=plan.frequency,
        allocated_amount=plan.allocated_amount,
        description=plan.description
    )
    store.upsert_investment_plan(p)
    return {"status": "success"}

@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int, store: DataStore = Depends(get_store)) -> Any:
    store.delete_investment_plan(plan_id)
    return {"status": "success"}


# --- Portfolio Endpoints ---

@router.get("/portfolio")
async def get_portfolio(store: DataStore = Depends(get_store)) -> Any:
    return store.get_portfolio_items()

@router.post("/portfolio")
async def upsert_portfolio_item(item: PortfolioItemInput, store: DataStore = Depends(get_store)) -> Any:
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
async def delete_portfolio_item(item_id: int, store: DataStore = Depends(get_store)) -> Any:
    store.delete_portfolio_item(item_id)
    return {"status": "success"}
