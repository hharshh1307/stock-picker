"""Alternative Assets & Macro Data Fetcher

Connects to real APIs for comprehensive cross-asset tracking:
1. Cryptocurrency (CoinGecko API)
2. Mutual Funds (mfapi.in)
3. Macro/Forex/Commodities (yfinance)
"""

import requests
import yfinance as yf
from utils import setup_logger

logger = setup_logger(__name__)

def fetch_crypto_prices(coins: list[str] = ["bitcoin", "ethereum", "solana", "ripple"]) -> dict:
    """Fetch current prices for major cryptocurrencies using CoinGecko."""
    try:
        coin_list = ",".join(coins)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_list}&vs_currencies=inr,usd"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching crypto data: {e}")
        return {"error": f"Could not fetch crypto data: {str(e)}"}

def search_mutual_fund(query: str) -> list[dict]:
    """Search for a mutual fund on mfapi.in and return the top matches."""
    try:
        url = f"https://api.mfapi.in/mf/search?q={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        results = response.json()
        return results[:5]  # return top 5 matches
    except Exception as e:
        logger.error(f"Error searching mutual fund: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

def fetch_mutual_fund_nav(scheme_code: str) -> dict:
    """Fetch the latest NAV and details for a specific mutual fund scheme."""
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        meta = data.get("meta", {})
        nav_data = data.get("data", [])
        
        latest_nav = nav_data[0] if nav_data else {}
        prev_nav = nav_data[1] if len(nav_data) > 1 else {}
        
        change = 0.0
        if latest_nav.get("nav") and prev_nav.get("nav"):
            latest = float(latest_nav["nav"])
            prev = float(prev_nav["nav"])
            change = ((latest - prev) / prev) * 100
            
        return {
            "fund_house": meta.get("fund_house"),
            "scheme_type": meta.get("scheme_type"),
            "scheme_category": meta.get("scheme_category"),
            "scheme_name": meta.get("scheme_name"),
            "latest_nav": latest_nav.get("nav"),
            "date": latest_nav.get("date"),
            "1_day_change_pct": round(change, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching mutual fund NAV: {e}")
        return {"error": f"Fetch failed: {str(e)}"}

def fetch_real_macro_environment() -> dict:
    """Fetch live macro data using yfinance.
    
    Includes: India VIX, USD/INR, Gold Futures, Brent Crude.
    """
    tickers = {
        "Nifty_VIX": "^INDIAVIX",
        "USD_INR": "INR=X",
        "Gold_Futures": "GC=F", 
        "Brent_Crude": "BZ=F"
    }
    
    macro_data = {}
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                latest = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                change_pct = ((latest - prev) / prev) * 100
                
                trend = "stable"
                if change_pct > 1.0:
                    trend = "rising strongly"
                elif change_pct > 0.2:
                    trend = "rising"
                elif change_pct < -1.0:
                    trend = "falling strongly"
                elif change_pct < -0.2:
                    trend = "falling"
                    
                macro_data[name] = {
                    "price": round(latest, 2),
                    "change_pct": round(change_pct, 2),
                    "trend": trend
                }
            else:
                macro_data[name] = {"error": "Insufficient data"}
        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")
            macro_data[name] = {"error": str(e)}

    # Add interpretive context
    vix = macro_data.get("Nifty_VIX", {}).get("price", 15)
    vix_interpretation = "Normal market conditions."
    if vix > 20:
        vix_interpretation = "High volatility/fear. Option premiums are expensive. High risk for naked directional bets."
    elif vix < 12:
        vix_interpretation = "Low volatility/complacency. Options are cheap to buy."

    usdinr = macro_data.get("USD_INR", {}).get("trend", "stable")
    rupee_interp = "Stable currency."
    if "rising" in usdinr:
        rupee_interp = "Rupee depreciating (USD getting stronger). Good for IT/Pharma exports, bad for importing sectors."
    elif "falling" in usdinr:
        rupee_interp = "Rupee appreciating. Positive for importers (FMCG, Auto), negative for IT."

    return {
        "indicators": macro_data,
        "interpretations": {
            "vix_insight": vix_interpretation,
            "rupee_insight": rupee_interp
        },
        "advisory": "Use VIX for F&O sizing. High VIX = hedge heavily, avoid selling naked options. Use USDINR to weight export vs import heavy sectors."
    }
