"""Agent tools — 16 tools for the Financial Expert Agent.

Each tool has:
1. A function implementation that queries the local database
2. An OpenAI function schema for the tool-calling API
"""

import json
from datetime import date, timedelta
from typing import Any

from data_store import DataStore
from market_intelligence import (
    get_financial_highlights,
    get_market_breadth,
    get_sector_performance,
    get_top_movers,
    get_volume_spikes,
)
from alternative_assets import (
    fetch_real_macro_environment,
    fetch_crypto_prices,
    search_mutual_fund,
    fetch_mutual_fund_nav
)

# --- Tool Implementations ---

def search_stocks(store: DataStore, query: str, sector: str | None = None) -> list[dict]:
    """Search for stocks by name, symbol, or sector."""
    if sector:
        stocks = store.get_stocks_by_sector(sector)
        # Filter by query within sector
        query_lower = query.lower() if query else ""
        if query_lower:
            stocks = [s for s in stocks if query_lower in s.symbol.lower() or query_lower in (s.company_name or "").lower()]
    else:
        stocks = store.search_stocks(query, limit=20)

    return [
        {
            "symbol": s.symbol,
            "company_name": s.company_name,
            "sector": s.sector,
            "industry": s.industry,
        }
        for s in stocks[:20]
    ]


def get_stock_info(store: DataStore, symbol: str) -> dict | None:
    """Get comprehensive stock profile with latest price, 52-week range, and ML signals."""
    detail = store.get_stock_detail(symbol.upper())
    if not detail:
        return None

    # Calculate 30-day change
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    row = store.conn.execute(
        """SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1""",
        (symbol.upper(), cutoff),
    ).fetchone()

    change_30d = None
    if row and detail.get("latest_price") and row["close"] > 0:
        change_30d = ((detail["latest_price"] - row["close"]) / row["close"]) * 100

    detail["change_30d"] = round(change_30d, 2) if change_30d else None

    # Inject ML signals from saved predictions
    try:
        from ml_pipeline import get_ml_predictions
        preds = get_ml_predictions()
        ml = preds.get(symbol.upper())
        if ml:
            detail["ml_signals"] = {
                "score_1m": ml.get("ml_1m_score"),
                "predicted_return_1m_pct": ml.get("predicted_return_1m"),
                "outperform_probability": ml.get("outperform_probability"),
                "is_likely_outperformer": ml.get("is_likely_outperformer"),
                "generated_at": ml.get("generated_at"),
            }
    except Exception:
        pass  # ML predictions optional — never block stock info

    return detail


def get_price_history(store: DataStore, symbol: str, days: int = 90) -> dict:
    """Get price history with technical indicators."""
    prices = store.get_price_series(symbol.upper(), days=days)
    if not prices:
        return {"error": f"No price data for {symbol}"}

    closes = [p["close"] for p in prices]
    volumes = [p["volume"] for p in prices]

    # Calculate simple moving averages
    def sma(data: list, period: int) -> float | None:
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    # Calculate RSI (14-day)
    def rsi(closes: list, period: int = 14) -> float | None:
        if len(closes) < period + 1:
            return None
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # Calculate volatility (std dev of daily returns)
    def volatility(closes: list, period: int = 20) -> float | None:
        if len(closes) < period + 1:
            return None
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        recent_returns = returns[-period:]
        mean = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean) ** 2 for r in recent_returns) / len(recent_returns)
        return (variance ** 0.5) * 100  # As percentage

    latest = prices[-1] if prices else {}
    earliest = prices[0] if prices else {}

    period_change = None
    if earliest.get("close") and latest.get("close") and earliest["close"] > 0:
        period_change = ((latest["close"] - earliest["close"]) / earliest["close"]) * 100

    return {
        "symbol": symbol.upper(),
        "period_days": days,
        "data_points": len(prices),
        "latest_price": latest.get("close"),
        "latest_date": latest.get("date"),
        "period_high": max(p["high"] for p in prices) if prices else None,
        "period_low": min(p["low"] for p in prices) if prices else None,
        "period_change_pct": round(period_change, 2) if period_change else None,
        "avg_volume": int(sum(volumes) / len(volumes)) if volumes else None,
        "sma_20": round(sma(closes, 20), 2) if sma(closes, 20) else None,
        "sma_50": round(sma(closes, 50), 2) if sma(closes, 50) else None,
        "rsi_14": round(rsi(closes), 2) if rsi(closes) else None,
        "volatility_20d": round(volatility(closes), 2) if volatility(closes) else None,
    }


def get_financials(store: DataStore, symbol: str, quarters: int = 4) -> list[dict]:
    """Get quarterly financial data."""
    summary = store.get_financials_summary(symbol.upper())
    return summary[:quarters]


def get_sector_performance_tool(store: DataStore, days: int = 30) -> list[dict]:
    """Get sector performance rankings."""
    perf = get_sector_performance(store, days=days)
    return [
        {
            "sector": s["sector"],
            "avg_return_pct": s["avg_change_pct"],
            "stock_count": s["stock_count"],
            "top_gainers": [g["symbol"] for g in s["top_gainers"][:3]],
            "top_losers": [l["symbol"] for l in s["top_losers"][:3]],
        }
        for s in perf
    ]


def get_top_movers_tool(store: DataStore, days: int = 30, limit: int = 10) -> dict:
    """Get top gaining and losing stocks."""
    movers = get_top_movers(store, days=days, limit=limit)
    return {
        "gainers": [
            {
                "symbol": g["symbol"],
                "company_name": g.get("company_name"),
                "sector": g.get("sector"),
                "change_pct": round(g["change_pct"], 2),
                "price": g.get("end_price"),
            }
            for g in movers.get("gainers", [])
        ],
        "losers": [
            {
                "symbol": l["symbol"],
                "company_name": l.get("company_name"),
                "sector": l.get("sector"),
                "change_pct": round(l["change_pct"], 2),
                "price": l.get("end_price"),
            }
            for l in movers.get("losers", [])
        ],
    }


def get_market_breadth_tool(store: DataStore, days: int = 30) -> dict:
    """Get market breadth indicators."""
    breadth = get_market_breadth(store, days=days)
    breadth_7d = get_market_breadth(store, days=7)

    sentiment = "NEUTRAL"
    if breadth["breadth_ratio"] > 1.5:
        sentiment = "STRONGLY_BULLISH"
    elif breadth["breadth_ratio"] > 1.2:
        sentiment = "BULLISH"
    elif breadth["breadth_ratio"] < 0.67:
        sentiment = "STRONGLY_BEARISH"
    elif breadth["breadth_ratio"] < 0.83:
        sentiment = "BEARISH"

    return {
        "sentiment": sentiment,
        "period_30d": {
            "advancing": breadth["advancing"],
            "declining": breadth["declining"],
            "unchanged": breadth["unchanged"],
            "total": breadth["total"],
            "breadth_ratio": breadth["breadth_ratio"],
            "advance_pct": breadth["advance_pct"],
        },
        "period_7d": {
            "advancing": breadth_7d["advancing"],
            "declining": breadth_7d["declining"],
            "breadth_ratio": breadth_7d["breadth_ratio"],
        },
    }


def get_volume_spikes_tool(store: DataStore, days: int = 5, threshold: float = 2.0) -> list[dict]:
    """Find stocks with unusual volume."""
    spikes = get_volume_spikes(store, days=days, threshold=threshold)
    return [
        {
            "symbol": s["symbol"],
            "company_name": s.get("company_name"),
            "sector": s.get("sector"),
            "volume_ratio": round(s["vol_ratio"], 2),
        }
        for s in spikes[:15]
    ]


def get_financial_highlights_tool(store: DataStore) -> dict:
    """Get market-wide financial standouts."""
    highlights = get_financial_highlights(store)

    # Top by revenue growth
    with_growth = [h for h in highlights if h.get("revenue_growth_qoq") is not None]
    with_growth.sort(key=lambda x: x["revenue_growth_qoq"], reverse=True)

    # Top by profit margin
    by_margin = sorted(highlights, key=lambda x: x.get("profit_margin", 0), reverse=True)

    return {
        "top_revenue_growth": [
            {
                "symbol": h["symbol"],
                "company_name": h["company_name"],
                "sector": h.get("sector"),
                "revenue_growth_qoq": h["revenue_growth_qoq"],
                "profit_margin": h["profit_margin"],
            }
            for h in with_growth[:10]
        ],
        "top_profit_margin": [
            {
                "symbol": h["symbol"],
                "company_name": h["company_name"],
                "sector": h.get("sector"),
                "profit_margin": h["profit_margin"],
            }
            for h in by_margin[:10]
        ],
    }


def get_news(store: DataStore, symbol: str | None = None, limit: int = 15) -> list[dict]:
    """Get news for a stock or general market news."""
    if symbol:
        news = store.get_stock_news(symbol.upper(), limit=limit)
    else:
        news = store.get_market_news(limit=limit)

    return [
        {
            "title": n.get("title"),
            "source": n.get("source_name"),
            "published_at": n.get("published_at"),
            "description": n.get("description", "")[:200] if n.get("description") else None,
        }
        for n in news
    ]


def compare_stocks(store: DataStore, symbols: list[str]) -> list[dict]:
    """Compare multiple stocks side by side."""
    if len(symbols) < 2 or len(symbols) > 5:
        return [{"error": "Please provide 2-5 stock symbols to compare"}]

    comparisons = []
    for sym in symbols:
        detail = store.get_stock_detail(sym.upper())
        if not detail:
            comparisons.append({"symbol": sym.upper(), "error": "Stock not found"})
            continue

        financials = store.get_financials_summary(sym.upper())
        latest_fin = financials[0] if financials else {}

        # Get 30-day and 90-day performance
        prices_30d = get_price_history(store, sym, days=30)
        prices_90d = get_price_history(store, sym, days=90)

        comparisons.append({
            "symbol": sym.upper(),
            "company_name": detail.get("company_name"),
            "sector": detail.get("sector"),
            "industry": detail.get("industry"),
            "latest_price": detail.get("latest_price"),
            "high_52w": detail.get("high_52w"),
            "low_52w": detail.get("low_52w"),
            "ytd_return": detail.get("ytd_return"),
            "change_30d": prices_30d.get("period_change_pct"),
            "change_90d": prices_90d.get("period_change_pct"),
            "rsi_14": prices_30d.get("rsi_14"),
            "volatility": prices_30d.get("volatility_20d"),
            "revenue": latest_fin.get("revenue"),
            "net_income": latest_fin.get("net_income"),
            "profit_margin": round((latest_fin["net_income"] / latest_fin["revenue"]) * 100, 2)
                if latest_fin.get("revenue") and latest_fin.get("net_income") and latest_fin["revenue"] > 0
                else None,
        })

    return comparisons


def calculate_valuation_metrics(store: DataStore, symbol: str) -> dict:
    """Calculate valuation metrics from financial data."""
    detail = store.get_stock_detail(symbol.upper())
    if not detail:
        return {"error": f"Stock {symbol} not found"}

    financials = store.get_financials_summary(symbol.upper())
    if not financials:
        return {"error": f"No financial data for {symbol}"}

    latest = financials[0]
    price = detail.get("latest_price")

    result = {
        "symbol": symbol.upper(),
        "company_name": detail.get("company_name"),
        "sector": detail.get("sector"),
        "latest_price": price,
        "period": latest.get("period"),
    }

    # We don't have shares outstanding, so we'll show what we can
    revenue = latest.get("revenue")
    net_income = latest.get("net_income")
    total_equity = latest.get("total_equity")
    total_debt = latest.get("total_debt")
    total_assets = latest.get("total_assets")
    free_cashflow = latest.get("free_cashflow")

    if revenue and net_income and revenue > 0:
        result["profit_margin_pct"] = round((net_income / revenue) * 100, 2)

    if total_equity and net_income and total_equity > 0:
        # Annualized ROE (multiply quarterly by 4)
        result["roe_pct"] = round((net_income * 4 / total_equity) * 100, 2)

    if total_debt is not None and total_equity and total_equity > 0:
        result["debt_to_equity"] = round(total_debt / total_equity, 2)

    if total_assets and total_equity and total_assets > 0:
        result["equity_ratio"] = round(total_equity / total_assets, 2)

    if free_cashflow:
        result["free_cashflow"] = free_cashflow
        result["fcf_positive"] = free_cashflow > 0

    if revenue:
        result["quarterly_revenue"] = revenue
        result["annualized_revenue"] = revenue * 4

    if net_income:
        result["quarterly_net_income"] = net_income
        result["annualized_net_income"] = net_income * 4

    return result


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for real-time information."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                }
                for r in results
            ]
    except Exception as e:
        return [{"error": f"Web search failed: {str(e)}"}]


def get_user_portfolio(store: DataStore) -> dict:
    """Get the user's current manual portfolio and profile."""
    items = store.get_portfolio_items()
    profile = store.get_user_profile()
    
    portfolio_value = sum(item.quantity * item.average_buy_price for item in items)
    
    return {
        "profile": {
            "risk_tolerance": profile.risk_tolerance if profile else "Unknown",
            "total_capital": profile.total_capital if profile else 0,
            "expected_returns": profile.expected_returns if profile else 0,
        },
        "total_portfolio_value": portfolio_value,
        "holdings": [
            {
                "symbol": item.symbol,
                "quantity": item.quantity,
                "average_buy_price": item.average_buy_price,
                "strategy_frequency": item.strategy_frequency,
            }
            for item in items
        ]
    }

def get_investment_plans(store: DataStore) -> list[dict]:
    """Get the user's configured investment plans (e.g., Weekly ₹500)."""
    plans = store.get_investment_plans()
    return [
        {
            "frequency": plan.frequency,
            "allocated_amount": plan.allocated_amount,
            "description": plan.description,
        }
        for plan in plans
    ]

def get_portfolio_analysis(store: DataStore) -> dict:
    """Get detailed portfolio P&L with ML signals for each holding."""
    from groww_integration import fetch_live_groww_portfolio, save_live_portfolio_to_cache
    from portfolio_analyzer import get_portfolio_pnl

    # Load ML predictions once
    try:
        from ml_pipeline import get_ml_predictions
        ml_preds = get_ml_predictions()
    except Exception:
        ml_preds = {}

    def _inject_ml(holding: dict) -> dict:
        sym = (holding.get("asset_name") or holding.get("symbol", "")).upper()
        ml = ml_preds.get(sym)
        if ml:
            holding["ml_signals"] = {
                "score_1m": ml.get("ml_1m_score"),
                "predicted_return_1m_pct": ml.get("predicted_return_1m"),
                "outperform_probability": ml.get("outperform_probability"),
                "is_likely_outperformer": ml.get("is_likely_outperformer"),
            }
        return holding

    # Transparent background sync
    live_result = fetch_live_groww_portfolio()
    if live_result.get("status") == "success":
        save_live_portfolio_to_cache(live_result["structured_portfolio"])
        result = {
            "source": "Groww Live Broker Connection",
            "holdings": [_inject_ml(h) for h in live_result["structured_portfolio"]],
        }
        if live_result.get("available_cash"):
            result["available_cash_inr"] = live_result["available_cash"]
        if live_result.get("user_profile"):
            prof = live_result["user_profile"]
            result["account_info"] = {
                "ucc": prof.get("ucc"),
                "active_segments": prof.get("active_segments", []),
                "ddpi_enabled": prof.get("ddpi_enabled"),
                "nse_enabled": prof.get("nse_enabled"),
                "bse_enabled": prof.get("bse_enabled"),
            }
        if live_result.get("intraday_positions"):
            result["intraday_positions"] = live_result["intraday_positions"]
        return result

    # Fallback to uploaded PDF
    pdf_result = get_uploaded_portfolio_pdf(store)
    if pdf_result.get("status") == "success":
        holdings = [_inject_ml(h) for h in pdf_result.get("structured_portfolio", [])]
        return {
            "source": f"Uploaded PDF Statement ({pdf_result.get('filename', 'cache')})",
            "holdings": holdings,
        }

    # Final fallback to local DB
    return get_portfolio_pnl(store)


def get_groww_position_for_symbol(store: DataStore, symbol: str) -> dict:
    """Fetch the current live position for a specific stock from Groww (CASH segment)."""
    from groww_integration import fetch_position_for_symbol
    return fetch_position_for_symbol(symbol)

def get_uploaded_portfolio_pdf(store: DataStore) -> dict:
    """Read and extract raw text from any uploaded PDF Demat portfolio statements.
    Use this to see the user's complete portfolio, including Mutual Funds, ETFs, and unlisted stocks.
    """
    import os
    import json
    import pdfplumber
    from pathlib import Path
    from openai import OpenAI
    
    portfolio_dir = Path("web/src/app/portfolio")
    if not portfolio_dir.exists():
        return {"error": "Portfolio directory not found.", "structured_portfolio": []}
        
    pdf_files = list(portfolio_dir.glob("*.pdf"))
    if not pdf_files:
        return {"error": "No PDF portfolio statements found.", "structured_portfolio": []}
        
    latest_pdf = max(pdf_files, key=os.path.getmtime)
    cache_file = portfolio_dir / f"{latest_pdf.stem}_structured.json"
    
    # Return cached structured data if it exists
    if cache_file.exists() and os.path.getmtime(cache_file) > os.path.getmtime(latest_pdf):
        with open(cache_file, "r") as f:
            return {"status": "success", "source": "cache", "structured_portfolio": json.load(f)}
    
    try:
        text = []
        with pdfplumber.open(latest_pdf) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
        raw_text = "\n".join(text)
        
        client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a financial data parser. Extract the user's portfolio from the raw Demat statement text into a JSON array named 'portfolio' with objects containing: 'asset_name', 'asset_type' (Equity/Mutual Fund/ETF), 'quantity' (number), 'rate' (number), 'total_value' (number)."},
                {"role": "user", "content": raw_text}
            ]
        )
        
        raw = response.choices[0].message.content.strip()
        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match: raw = json_match.group(0)
        structured_data = json.loads(raw).get("portfolio", [])
        
        with open(cache_file, "w") as f:
            json.dump(structured_data, f, indent=2)
            
        return {"status": "success", "source": "parsed_pdf", "structured_portfolio": structured_data}
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}", "structured_portfolio": []}

def get_live_broker_portfolio(store: DataStore) -> dict:
    """Fetch the real-time live portfolio directly from the connected Groww broker account."""
    from groww_integration import fetch_live_groww_portfolio, save_live_portfolio_to_cache
    
    result = fetch_live_groww_portfolio()
    if result.get("status") == "success":
        save_live_portfolio_to_cache(result["structured_portfolio"])
    
    return result

def get_portfolio_risk(store: DataStore) -> dict:
    """Get portfolio risk analysis: concentration, sectors, diversification."""
    from portfolio_analyzer import get_portfolio_risk_analysis
    return get_portfolio_risk_analysis(store)

def run_strategy_simulation(store: DataStore, frequency: str, iterations: int = 10) -> dict:
    """Run a historical backtest simulation for a specific frequency strategy."""
    from backtester import run_simulation
    return run_simulation(frequency, iterations)

def get_strategy_recommendation(store: DataStore, frequency: str, amount: float | None = None) -> dict:
    """Get investment recommendations for a specific frequency."""
    from portfolio_analyzer import get_strategy_recommendations
    # If amount not provided, look up from plans
    if amount is None:
        plans = store.get_investment_plans()
        for p in plans:
            if p.frequency.lower() == frequency.lower():
                amount = p.allocated_amount
                break
        if amount is None:
            amount = 1000  # default
    return get_strategy_recommendations(store, frequency, amount)


def get_macro_environment(store: DataStore) -> dict:
    """Get real-time macroeconomic indicators (VIX, USDINR, Gold, Crude)."""
    return fetch_real_macro_environment()

def get_crypto_market(store: DataStore) -> dict:
    """Get top cryptocurrency prices."""
    return fetch_crypto_prices()

def search_mutual_funds(store: DataStore, query: str) -> list[dict]:
    """Search for mutual funds and get their latest NAV."""
    results = search_mutual_fund(query)
    # Automatically try to fetch NAV for the top result to give immediate value
    if results and "error" not in results[0] and results[0].get("schemeCode"):
        top_fund_data = fetch_mutual_fund_nav(str(results[0]["schemeCode"]))
        results[0]["nav_details"] = top_fund_data
    return results

def get_screener_data_tool(store: DataStore, symbol: str) -> dict:
    """Fetch rich fundamental data from Screener.in: PE, PB, ROE, ROCE, promoter holding, quarterly P&L, peer comparison."""
    from screener_scraper import get_screener_data, format_screener_for_agent
    data = get_screener_data(symbol.upper(), store)
    return {
        "raw": data,
        "formatted": format_screener_for_agent(data),
    }


# --- OpenAI Function Schemas ---

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_stocks",
            "description": "Search for stocks by name, symbol, or sector. Use this to find stock symbols when the user mentions a company name or wants to explore a sector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term: company name, symbol, or keyword"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Optional: filter by sector (e.g., 'Technology', 'Financial Services')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": "Get comprehensive stock profile including latest price, 52-week range, YTD return, and company info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol (e.g., 'RELIANCE', 'TCS')"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": "Get price history with technical indicators like SMA, RSI, and volatility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of history (default: 90)",
                        "default": 90
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": "Get quarterly financial data including revenue, net income, EBITDA, and cash flow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol"
                    },
                    "quarters": {
                        "type": "integer",
                        "description": "Number of quarters to retrieve (default: 4)",
                        "default": 4
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_performance",
            "description": "Get sector performance rankings with top gainers and losers in each sector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Performance period in days (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_movers",
            "description": "Get top gaining and losing stocks in the market.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Period in days (default: 30)",
                        "default": 30
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of movers to return (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_breadth",
            "description": "Get market breadth indicators: advancing vs declining stocks, sentiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Period in days (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_volume_spikes",
            "description": "Find stocks with unusual trading volume, indicating potential price moves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Recent period to check (default: 5)",
                        "default": 5
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Volume ratio threshold (default: 2.0 = 2x average)",
                        "default": 2.0
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_highlights",
            "description": "Get market-wide financial standouts: top revenue growth, highest profit margins.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get recent news articles for a stock or general market news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol for specific news, or omit for market news"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of articles (default: 15)",
                        "default": 15
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_stocks",
            "description": "Compare 2-5 stocks side by side with key metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2-5 stock symbols to compare"
                    }
                },
                "required": ["symbols"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_valuation_metrics",
            "description": "Calculate valuation and profitability metrics for a stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time news or information not in the local database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_portfolio",
            "description": "Get the user's current portfolio holdings, total value, and risk profile.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_investment_plans",
            "description": "Get the user's configured investment plans (e.g., Daily, Weekly, Monthly allocations).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_analysis",
            "description": "Get detailed portfolio P&L analysis with current market prices, unrealized gains/losses per holding, and overall portfolio performance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_uploaded_portfolio_pdf",
            "description": "Extract raw text from uploaded Demat portfolio PDFs to analyze Mutual Funds, ETFs, and non-Nifty500 holdings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_broker_portfolio",
            "description": "Fetch the real-time live portfolio holdings, available cash balance, and account info directly from the connected Groww broker API.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_groww_position_for_symbol",
            "description": "Fetch the current live position for a specific stock from Groww (CASH segment). Use this when the user asks about a single holding's current position, realised P&L, or quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE trading symbol (e.g., 'RELIANCE', 'TCS')"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_risk",
            "description": "Analyze portfolio risk: sector allocation, concentration (HHI), diversification score, frequency strategy breakdown, volatility per holding, and actionable diversification suggestions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_strategy_recommendation",
            "description": "Get investment recommendations for a specific frequency (Daily/Weekly/Monthly/Yearly). Scores stocks using technicals+fundamentals appropriate for the time horizon, provides market timing signal, and suggests specific stock allocations with reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "frequency": {
                        "type": "string",
                        "description": "Investment frequency: 'Daily', 'Weekly', 'Monthly', 'Yearly', or 'Long-term'",
                        "enum": ["Daily", "Weekly", "Monthly", "Yearly", "Long-term"]
                    },
                    "amount": {
                        "type": "number",
                        "description": "Optional: budget amount in INR. If not provided, uses the amount from the user's investment plan for that frequency."
                    }
                },
                "required": ["frequency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_strategy_simulation",
            "description": "Run a historical backtest simulation to calculate the expected financial gain, win rate, and max drawdown of a strategy over a specific frequency.",
            "parameters": {
                "type": "object",
                "properties": {
                    "frequency": {
                        "type": "string",
                        "description": "Investment frequency to backtest (Daily, Weekly, Monthly, Yearly)",
                        "enum": ["Daily", "Weekly", "Monthly", "Yearly"]
                    },
                    "iterations": {
                        "type": "integer",
                        "description": "Number of past iterations to simulate (default is 10)"
                    }
                },
                "required": ["frequency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_environment",
            "description": "Get broader macroeconomic indicators (Nifty VIX, USDINR, Gold, Crude Oil) to assess overall market risk, cross-asset correlations, and suitability for Futures & Options (F&O) trading.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_market",
            "description": "Get real-time prices for major cryptocurrencies (Bitcoin, Ethereum, Solana, Ripple) in INR and USD using the CoinGecko API. Useful for assessing global risk appetite.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_mutual_funds",
            "description": "Search for Indian Mutual Funds and fetch their latest NAV and daily change percentage using mfapi.in. Use this to track passive investments or provide diversification options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The name or part of the name of the mutual fund (e.g., 'SBI Small Cap', 'Parag Parikh Flexi')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screener_data",
            "description": (
                "Fetch rich fundamental data from Screener.in for a stock. "
                "Returns: PE ratio, PB ratio, ROE, ROCE (3yr), Market Cap, Book Value, Dividend Yield, "
                "Promoter/FII/DII/Public shareholding %, Screener's own pros & cons analysis, "
                "quarterly P&L (last 8 quarters: Sales, Net Profit, OPM%), annual P&L trend (5 years), "
                "balance sheet highlights, cash flow, and peer comparison table. "
                "Use this for any deep fundamental analysis, comparison, or when user asks about valuation, "
                "ownership, or financial quality. Always prefer this over get_financials for fundamentals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol (e.g., 'RELIANCE', 'HDFCBANK', 'INFY')"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
]


def execute_tool(store: DataStore, tool_name: str, arguments: dict[str, Any]) -> Any:
    """Execute a tool by name with the given arguments."""
    tool_map = {
        "search_stocks": lambda args: search_stocks(store, args.get("query", ""), args.get("sector")),
        "get_stock_info": lambda args: get_stock_info(store, args["symbol"]),
        "get_price_history": lambda args: get_price_history(store, args["symbol"], args.get("days", 90)),
        "get_financials": lambda args: get_financials(store, args["symbol"], args.get("quarters", 4)),
        "get_sector_performance": lambda args: get_sector_performance_tool(store, args.get("days", 30)),
        "get_top_movers": lambda args: get_top_movers_tool(store, args.get("days", 30), args.get("limit", 10)),
        "get_market_breadth": lambda args: get_market_breadth_tool(store, args.get("days", 30)),
        "get_volume_spikes": lambda args: get_volume_spikes_tool(store, args.get("days", 5), args.get("threshold", 2.0)),
        "get_financial_highlights": lambda args: get_financial_highlights_tool(store),
        "get_news": lambda args: get_news(store, args.get("symbol"), args.get("limit", 15)),
        "compare_stocks": lambda args: compare_stocks(store, args["symbols"]),
        "calculate_valuation_metrics": lambda args: calculate_valuation_metrics(store, args["symbol"]),
        "web_search": lambda args: web_search(args["query"], args.get("max_results", 10)),
        "get_user_portfolio": lambda args: get_user_portfolio(store),
        "get_investment_plans": lambda args: get_investment_plans(store),
        "get_portfolio_analysis": lambda args: get_portfolio_analysis(store),
        "get_uploaded_portfolio_pdf": lambda args: get_uploaded_portfolio_pdf(store),
        "get_live_broker_portfolio": lambda args: get_live_broker_portfolio(store),
        "get_groww_position_for_symbol": lambda args: get_groww_position_for_symbol(store, args["symbol"]),
        "get_portfolio_risk": lambda args: get_portfolio_risk(store),
        "run_strategy_simulation": lambda args: run_strategy_simulation(store, args["frequency"], args.get("iterations", 10)),
        "get_strategy_recommendation": lambda args: get_strategy_recommendation(store, args["frequency"], args.get("amount")),
        "get_macro_environment": lambda args: get_macro_environment(store),
        "get_crypto_market": lambda args: get_crypto_market(store),
        "search_mutual_funds": lambda args: search_mutual_funds(store, args["query"]),
        "get_screener_data": lambda args: get_screener_data_tool(store, args["symbol"]),
    }

    if tool_name not in tool_map:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return tool_map[tool_name](arguments)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
