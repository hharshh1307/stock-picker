"""Portfolio Analyzer — Deep portfolio analysis for the Financial Expert Agent.

Provides portfolio-level metrics: P&L, diversification, concentration risk,
sector allocation, and frequency-based strategy analysis.
"""

import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from data_store import DataStore
from utils import setup_logger

logger = setup_logger(__name__)


def get_portfolio_pnl(store: DataStore) -> dict:
    """Calculate detailed P&L for every holding with current market prices."""
    items = store.get_portfolio_items()
    profile = store.get_user_profile()
    if not items:
        return {"error": "No portfolio holdings found", "holdings": []}

    holdings = []
    total_invested = 0.0
    total_current = 0.0

    for item in items:
        # Get latest price
        latest = store.conn.execute(
            "SELECT close, date FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (item.symbol,),
        ).fetchone()

        current_price = latest["close"] if latest else None
        price_date = latest["date"] if latest else None

        invested_value = item.quantity * item.average_buy_price
        current_value = item.quantity * current_price if current_price else None
        pnl = current_value - invested_value if current_value else None
        pnl_pct = (pnl / invested_value * 100) if pnl is not None and invested_value > 0 else None

        # Get stock info for sector
        stock = store.get_stock(item.symbol)

        # Get 30-day performance
        cutoff_30d = (date.today() - timedelta(days=30)).isoformat()
        price_30d = store.conn.execute(
            "SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1",
            (item.symbol, cutoff_30d),
        ).fetchone()
        change_30d = None
        if price_30d and current_price and price_30d["close"] > 0:
            change_30d = ((current_price - price_30d["close"]) / price_30d["close"]) * 100

        total_invested += invested_value
        if current_value:
            total_current += current_value

        holdings.append({
            "symbol": item.symbol,
            "company_name": stock.company_name if stock else item.symbol,
            "sector": stock.sector if stock else None,
            "quantity": item.quantity,
            "avg_buy_price": round(item.average_buy_price, 2),
            "current_price": round(current_price, 2) if current_price else None,
            "price_date": price_date,
            "invested_value": round(invested_value, 2),
            "current_value": round(current_value, 2) if current_value else None,
            "unrealized_pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
            "change_30d_pct": round(change_30d, 2) if change_30d is not None else None,
            "strategy_frequency": item.strategy_frequency,
        })

    total_pnl = total_current - total_invested if total_current > 0 else None
    total_pnl_pct = (total_pnl / total_invested * 100) if total_pnl is not None and total_invested > 0 else None

    return {
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_unrealized_pnl": round(total_pnl, 2) if total_pnl is not None else None,
        "total_pnl_pct": round(total_pnl_pct, 2) if total_pnl_pct is not None else None,
        "holding_count": len(holdings),
        "risk_tolerance": profile.risk_tolerance if profile else "unknown",
        "total_capital": profile.total_capital if profile else 0,
        "capital_deployed_pct": round(total_invested / profile.total_capital * 100, 1)
            if profile and profile.total_capital > 0 else None,
        "holdings": holdings,
    }


def get_portfolio_risk_analysis(store: DataStore) -> dict:
    """Analyze portfolio risk: concentration, sector allocation, diversification."""
    pnl_data = get_portfolio_pnl(store)
    if "error" in pnl_data and not pnl_data.get("holdings"):
        return pnl_data

    holdings = pnl_data["holdings"]
    total_value = pnl_data["total_current_value"] or pnl_data["total_invested"]
    if total_value <= 0:
        return {"error": "Portfolio has no value"}

    # Sector allocation
    sector_alloc = defaultdict(float)
    for h in holdings:
        sector = h.get("sector") or "Unknown"
        value = h.get("current_value") or h.get("invested_value", 0)
        sector_alloc[sector] += value

    sector_breakdown = [
        {"sector": s, "value": round(v, 2), "weight_pct": round(v / total_value * 100, 1)}
        for s, v in sorted(sector_alloc.items(), key=lambda x: x[1], reverse=True)
    ]

    # Concentration risk (HHI — Herfindahl-Hirschman Index)
    weights = []
    for h in holdings:
        value = h.get("current_value") or h.get("invested_value", 0)
        w = value / total_value if total_value > 0 else 0
        weights.append(w)

    hhi = sum(w * w for w in weights)
    # HHI: 1.0 = single stock, 1/N = perfectly diversified
    n = len(holdings)
    max_diversified_hhi = 1 / n if n > 0 else 1

    if hhi > 0.5:
        concentration = "VERY_HIGH"
    elif hhi > 0.25:
        concentration = "HIGH"
    elif hhi > 0.15:
        concentration = "MODERATE"
    else:
        concentration = "LOW"

    # Frequency strategy breakdown
    freq_alloc = defaultdict(lambda: {"count": 0, "invested": 0, "current": 0, "symbols": []})
    for h in holdings:
        freq = h.get("strategy_frequency") or "Unassigned"
        freq_alloc[freq]["count"] += 1
        freq_alloc[freq]["invested"] += h.get("invested_value", 0)
        freq_alloc[freq]["current"] += h.get("current_value") or h.get("invested_value", 0)
        freq_alloc[freq]["symbols"].append(h["symbol"])

    frequency_breakdown = {
        freq: {
            "count": data["count"],
            "invested": round(data["invested"], 2),
            "current_value": round(data["current"], 2),
            "pnl": round(data["current"] - data["invested"], 2),
            "symbols": data["symbols"],
        }
        for freq, data in freq_alloc.items()
    }

    # Top holding weight
    top_holding = max(holdings, key=lambda h: h.get("current_value") or h.get("invested_value", 0))
    top_weight = ((top_holding.get("current_value") or top_holding.get("invested_value", 0)) / total_value * 100)

    # Volatility assessment per holding
    volatilities = []
    for h in holdings:
        prices = store.get_price_series(h["symbol"], days=90)
        if len(prices) > 20:
            closes = [p["close"] for p in prices]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            recent = returns[-20:]
            mean = sum(recent) / len(recent)
            var = sum((r - mean) ** 2 for r in recent) / len(recent)
            vol = (var ** 0.5) * 100
            volatilities.append({"symbol": h["symbol"], "volatility_20d": round(vol, 2)})

    avg_vol = sum(v["volatility_20d"] for v in volatilities) / len(volatilities) if volatilities else None

    return {
        "summary": pnl_data,
        "sector_allocation": sector_breakdown,
        "sector_count": len(sector_breakdown),
        "concentration": {
            "hhi": round(hhi, 4),
            "level": concentration,
            "top_holding": top_holding["symbol"],
            "top_holding_weight_pct": round(top_weight, 1),
        },
        "frequency_breakdown": frequency_breakdown,
        "volatility": {
            "per_holding": volatilities,
            "portfolio_avg_volatility": round(avg_vol, 2) if avg_vol else None,
        },
        "diversification_suggestions": _get_diversification_tips(
            sector_breakdown, concentration, len(holdings), pnl_data.get("risk_tolerance", "medium")
        ),
    }


def _get_diversification_tips(sectors: list, concentration: str, holding_count: int, risk: str) -> list[str]:
    """Generate actionable diversification tips."""
    tips = []
    if holding_count < 5:
        tips.append(f"Portfolio has only {holding_count} stocks. Consider adding 5-10 more across different sectors for better diversification.")
    if concentration in ("VERY_HIGH", "HIGH"):
        tips.append("High concentration risk. Consider spreading investments more evenly across holdings.")
    if len(sectors) < 3:
        tips.append(f"Only {len(sectors)} sector(s) represented. Add exposure to defensive sectors (FMCG, Pharma) and growth sectors (IT, Financials).")
    if sectors and sectors[0]["weight_pct"] > 50:
        tips.append(f"{sectors[0]['sector']} is {sectors[0]['weight_pct']}% of portfolio. Consider reducing to under 30%.")
    if risk == "high" and holding_count < 8:
        tips.append("High risk tolerance with few stocks — consider adding mid-cap/small-cap exposure for growth.")
    return tips


def get_strategy_recommendations(store: DataStore, frequency: str, amount: float) -> dict:
    """Get investment recommendations for a specific frequency and amount.
    
    Uses technical + fundamental signals appropriate for the time horizon.
    """
    all_changes = []
    cutoff_map = {
        "Daily": 30, "Weekly": 14, "Monthly": 60, "Yearly": 365, "Long-term": 365,
    }
    lookback = cutoff_map.get(frequency, 30)
    
    cutoff = (date.today() - timedelta(days=lookback)).isoformat()
    
    # Get all stocks with price data
    rows = store.conn.execute("""
        WITH price_range AS (
            SELECT p.symbol, s.company_name, s.sector, s.industry,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date ASC) as start_price,
                   FIRST_VALUE(p.close) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as end_price,
                   FIRST_VALUE(p.volume) OVER (PARTITION BY p.symbol ORDER BY p.date DESC) as latest_volume
            FROM prices p
            JOIN stocks s ON p.symbol = s.symbol
            WHERE p.date >= ? AND s.sector IS NOT NULL
        )
        SELECT DISTINCT symbol, company_name, sector, industry, start_price, end_price, latest_volume,
               CASE WHEN start_price > 0 THEN ((end_price - start_price) / start_price) * 100 ELSE 0 END as change_pct
        FROM price_range
        WHERE start_price > 0
    """, (cutoff,)).fetchall()
    
    stocks_data = [dict(r) for r in rows]
    
    # Pre-filter: only score top candidates based on frequency heuristic
    try:
        from ml_pipeline import get_ml_predictions
        ml_preds = get_ml_predictions()
    except Exception as e:
        ml_preds = {}

    if frequency == "Daily":
        # Daily: prefer stocks with recent moderate moves and decent volume
        stocks_data.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=False)
        candidates = [s for s in stocks_data if -10 < s.get("change_pct", 0) < 15][:150]
    elif frequency == "Weekly":
        # Weekly: prefer positive momentum
        stocks_data.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        candidates = stocks_data[:80]
    elif frequency == "Monthly":
        candidates = stocks_data[:80]  # Will be re-scored by fundamentals
    else:
        candidates = stocks_data[:80]
    
    # Score stocks based on True ML Pipeline strategy
    scored = []
    for s in candidates:
        sym = s["symbol"]
        
        # If we have ML predictions, use them!
        if ml_preds and sym in ml_preds:
            ml_data = ml_preds[sym]
            
            daily_score = ml_data["ml_1_day_momentum_score"]
            weekly_score = ml_data["ml_1_week_trend_score"]
            monthly_score = ml_data["ml_1_month_value_score"]
            yearly_score = ml_data["ml_1_year_fundamental_score"]
            
            # The primary score dictating rank is based on the requested frequency
            if frequency == "Daily":
                primary_score = daily_score
            elif frequency == "Weekly":
                primary_score = weekly_score
            elif frequency == "Monthly":
                primary_score = monthly_score
            else:
                primary_score = yearly_score
                
            scored.append({
                **s, 
                "score": primary_score,
                "ml_scores": {
                    "1_day_momentum_score": round(daily_score, 1),
                    "1_week_trend_score": round(weekly_score, 1),
                    "1_month_value_score": round(monthly_score, 1),
                    "1_year_fundamental_score": round(yearly_score, 1),
                }
            })
        else:
            # Fallback to legacy heuristics if ML is disabled/missing
            score = _score_stock_for_frequency(store, s, frequency)
            if score is not None:
                daily_score = _score_stock_for_frequency(store, s, "Daily") or 0
                weekly_score = _score_stock_for_frequency(store, s, "Weekly") or 0
                monthly_score = _score_stock_for_frequency(store, s, "Monthly") or 0
                yearly_score = _score_stock_for_frequency(store, s, "Yearly") or 0
                
                scored.append({
                    **s, 
                    "score": score,
                    "ml_scores": {
                        "1_day_momentum_score": round(daily_score, 1),
                        "1_week_trend_score": round(weekly_score, 1),
                        "1_month_value_score": round(monthly_score, 1),
                        "1_year_fundamental_score": round(yearly_score, 1),
                    }
                })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_picks = scored[:5]
    
    # Market timing signal
    from market_intelligence import get_market_breadth
    breadth = get_market_breadth(store, days=7)
    breadth_30d = get_market_breadth(store, days=30)
    
    invest_today = True
    timing_reason = "Market conditions are neutral — proceed with planned investment."
    
    ratio_7d = breadth.get("breadth_ratio", 1.0)
    ratio_30d = breadth_30d.get("breadth_ratio", 1.0)
    
    if ratio_7d < 0.5 and ratio_30d < 0.7:
        invest_today = False
        timing_reason = "Market is showing strong bearish momentum in both short and medium term. Consider waiting or investing a reduced amount."
    elif ratio_7d > 2.0:
        timing_reason = "Market is very bullish short-term. Good time to invest, but be aware of potential pullback."
    elif ratio_7d < 0.7:
        timing_reason = "Short-term weakness detected. Consider investing a smaller portion and saving the rest for better entry."
    
    # Allocation across top picks
    allocations = []
    if top_picks and invest_today:
        # Weight by score
        total_score = sum(p["score"] for p in top_picks)
        for p in top_picks:
            weight = p["score"] / total_score if total_score > 0 else 1 / len(top_picks)
            alloc_amount = round(amount * weight, 2)
            allocations.append({
                "symbol": p["symbol"],
                "company_name": p["company_name"],
                "sector": p["sector"],
                "score": round(p["score"], 2),
                "ml_scores": p["ml_scores"],
                "weight_pct": round(weight * 100, 1),
                "suggested_amount": alloc_amount,
                "current_price": round(p["end_price"], 2),
                "period_change_pct": round(p["change_pct"], 2),
                "reason": _get_pick_reason(p, frequency),
            })
    
    return {
        "frequency": frequency,
        "budget": amount,
        "invest_today": invest_today,
        "timing_signal": timing_reason,
        "market_breadth_7d": round(ratio_7d, 2),
        "market_breadth_30d": round(ratio_30d, 2),
        "top_picks": allocations,
        "strategy_description": _get_strategy_description(frequency),
    }


def _score_stock_for_frequency(store: DataStore, stock: dict, frequency: str) -> Optional[float]:
    """Score a stock from 0-100 based on the frequency strategy."""
    symbol = stock["symbol"]
    change = stock.get("change_pct", 0)
    
    # Get technical data
    prices = store.get_price_series(symbol, days=90)
    if len(prices) < 20:
        return None
    
    closes = [p["close"] for p in prices]
    volumes = [p["volume"] for p in prices]
    
    # RSI
    rsi = _calc_rsi(closes)
    
    # Volatility
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    recent_returns = returns[-20:]
    mean_ret = sum(recent_returns) / len(recent_returns) if recent_returns else 0
    var = sum((r - mean_ret) ** 2 for r in recent_returns) / len(recent_returns) if recent_returns else 0
    volatility = (var ** 0.5) * 100
    
    # Volume trend (recent vs avg)
    avg_vol = sum(volumes) / len(volumes) if volumes else 1
    recent_vol = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else avg_vol
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
    
    # SMA trend
    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    above_sma20 = closes[-1] > sma_20 if sma_20 else False
    above_sma50 = closes[-1] > sma_50 if sma_50 else False
    
    score = 50.0  # Base
    
    if frequency == "Daily":
        # Daily: mean reversion + momentum + volume
        if rsi and rsi < 35:
            score += 20  # Oversold bounce opportunity
        elif rsi and rsi > 70:
            score -= 15  # Overbought risk
        if vol_ratio > 1.5:
            score += 10  # Volume confirmation
        if 0 < change < 5:
            score += 10  # Mild positive momentum
        if volatility > 2:
            score += 5   # Needs vol for daily trades
        if volatility > 5:
            score -= 10  # Too volatile
            
    elif frequency == "Weekly":
        # Weekly: trend following + breakout
        if above_sma20:
            score += 15
        if above_sma50:
            score += 10
        if rsi and 40 < rsi < 65:
            score += 10  # Healthy trend zone
        if vol_ratio > 1.3:
            score += 8
        if 2 < change < 15:
            score += 12  # Good momentum
            
    elif frequency == "Monthly":
        # Monthly: value + quality + moderate growth
        score += _fundamental_score(store, symbol) * 0.4
        if above_sma50:
            score += 10
        if rsi and 30 < rsi < 60:
            score += 8  # Not overbought
        if -5 < change < 20:
            score += 5
            
    elif frequency in ("Yearly", "Long-term"):
        # Yearly: deep value + quality + growth
        score += _fundamental_score(store, symbol) * 0.6
        if above_sma50:
            score += 5
        if volatility and volatility < 3:
            score += 8  # Prefer stable for long-term
        if rsi and rsi < 50:
            score += 5  # Better entry points
    
    return max(0, min(100, score))


def _calc_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Calculate RSI."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _fundamental_score(store: DataStore, symbol: str) -> float:
    """Score 0-100 based on fundamentals (revenue growth, margins, debt)."""
    financials = store.get_financials_summary(symbol)
    if not financials or len(financials) < 2:
        return 30  # Neutral if no data
    
    score = 40.0
    latest = financials[0]
    prev = financials[1]
    
    # Revenue growth
    rev = latest.get("revenue")
    prev_rev = prev.get("revenue")
    if rev and prev_rev and prev_rev > 0:
        growth = (rev - prev_rev) / prev_rev * 100
        if growth > 15:
            score += 20
        elif growth > 5:
            score += 10
        elif growth < -5:
            score -= 10
    
    # Profit margin
    if rev and latest.get("net_income") and rev > 0:
        margin = latest["net_income"] / rev * 100
        if margin > 15:
            score += 15
        elif margin > 5:
            score += 8
        elif margin < 0:
            score -= 15
    
    # Debt health
    debt = latest.get("total_debt")
    equity = latest.get("total_equity")
    if debt is not None and equity and equity > 0:
        de_ratio = debt / equity
        if de_ratio < 0.5:
            score += 10
        elif de_ratio > 2:
            score -= 10
    
    # Free cash flow
    fcf = latest.get("free_cashflow")
    if fcf and fcf > 0:
        score += 8
    
    return max(0, min(100, score))


def _get_pick_reason(stock: dict, frequency: str) -> str:
    """Generate a brief reason for the stock pick."""
    reasons = {
        "Daily": "Short-term technical signals favorable for quick momentum play.",
        "Weekly": "Trend following setup with good volume confirmation.",
        "Monthly": "Solid fundamentals with reasonable entry point for medium-term accumulation.",
        "Yearly": "Strong long-term value with quality fundamentals and growth trajectory.",
        "Long-term": "Deep value with strong competitive position for wealth building.",
    }
    return reasons.get(frequency, "Meets scoring criteria for this investment horizon.")


def _get_strategy_description(frequency: str) -> str:
    """Describe the strategy approach for a frequency."""
    descs = {
        "Daily": "Intraday/overnight momentum — targets stocks with mean-reversion potential, healthy volume, and controlled volatility. Some days it's better NOT to invest.",
        "Weekly": "Swing trading — follows medium-term trends, buys breakouts above moving averages with volume confirmation.",
        "Monthly": "Value accumulation — blends fundamental quality (revenue growth, margins, low debt) with reasonable technical entry points.",
        "Yearly": "Long-term wealth building — prioritizes deep fundamental value, quality metrics, and stable growth over short-term price action.",
        "Long-term": "Buy-and-hold compounding — focuses on competitive moats, consistent growth, and superior capital allocation.",
    }
    return descs.get(frequency, "Balanced approach combining technicals and fundamentals.")
