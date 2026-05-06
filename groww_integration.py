import os
import json
import logging

logger = logging.getLogger(__name__)


def _build_groww_client():
    """
    Authenticate with Groww API and return an initialised GrowwAPI instance.

    Auth priority:
      1. TOTP flow (no daily re-approval required) — uses GROWW_TOTP_SECRET + GROWW_TOKEN
      2. API Key + Secret flow — uses GROWW_TOKEN + GROWW_API_SECRET
    """
    from dotenv import load_dotenv
    load_dotenv()

    from growwapi import GrowwAPI

    api_key = os.getenv("GROWW_TOKEN")
    secret = os.getenv("GROWW_API_SECRET")
    totp_secret = os.getenv("GROWW_TOTP_SECRET")

    if not api_key:
        raise ValueError("GROWW_TOKEN not found in environment variables.")

    access_token = None

    # 1st preference: TOTP flow — no expiry, no daily approval needed
    if totp_secret:
        try:
            import pyotp  # only needed when TOTP is configured
            totp = pyotp.TOTP(totp_secret).now()
            access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
            logger.info("Groww auth: TOTP flow succeeded.")
        except Exception as e:
            logger.warning(f"TOTP auth failed, falling back to API key+secret: {e}")

    # 2nd preference: API Key + Secret flow
    if access_token is None and secret:
        try:
            raw = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
            # SDK returns the token directly or wrapped in a dict
            if isinstance(raw, str):
                access_token = raw
            elif isinstance(raw, dict):
                access_token = raw.get("access_token") or raw.get("token") or raw
            logger.info("Groww auth: API key+secret flow succeeded.")
        except Exception as e:
            logger.warning(f"API key+secret auth failed: {e}")

    # Final fallback: treat raw GROWW_TOKEN as a bearer token directly
    if access_token is None:
        logger.warning("Both auth flows failed. Using raw GROWW_TOKEN as bearer token.")
        access_token = api_key

    return GrowwAPI(access_token)


def fetch_live_groww_portfolio() -> dict:
    """
    Fetches the live portfolio from the Groww API and maps it to the unified
    structured format the AI Agent expects.

    Returns a dict with keys:
      - status: "success" | "error"
      - source: str
      - user_profile: dict (vendor_user_id, ucc, nse_enabled, bse_enabled,
                            ddpi_enabled, active_segments)
      - available_cash: float (CNC balance available in the equity account)
      - structured_portfolio: list of holding dicts
      - intraday_positions: list of cash-segment intraday position dicts
      - error: str (only on failure)
    """
    try:
        groww = _build_groww_client()

        # ── 1. User profile ──────────────────────────────────────────────────
        user_profile = {}
        try:
            user_profile = groww.get_user_profile() or {}
            logger.info(f"Groww user profile fetched: ucc={user_profile.get('ucc')}")
        except Exception as e:
            logger.warning(f"get_user_profile failed: {e}")

        # ── 2. Available margin / buying power ───────────────────────────────
        available_cash = 0.0
        try:
            margin = groww.get_available_margin_details() or {}
            equity_details = margin.get("equity_margin_details", {})
            available_cash = float(equity_details.get("cnc_balance_available", 0))
            logger.info(f"Available CNC cash: ₹{available_cash:,.2f}")
        except Exception as e:
            logger.warning(f"get_available_margin_details failed: {e}")

        # ── 3. Holdings (long-term DEMAT delivery stocks) ────────────────────
        raw_holdings = {}
        try:
            raw_holdings = groww.get_holdings_for_user(timeout=10) or {}
            logger.info(f"Holdings response keys: {list(raw_holdings.keys())}")
        except Exception as e:
            logger.warning(f"get_holdings_for_user failed: {e}")

        # The API wraps holdings under "holdings" key (NOT "data")
        holdings_list = raw_holdings.get("holdings", [])
        if not holdings_list and isinstance(raw_holdings, list):
            holdings_list = raw_holdings  # defensive: handle bare list

        structured_portfolio = []
        for item in holdings_list:
            qty = float(item.get("quantity", 0))
            avg_price = float(item.get("average_price", 0))   # ← correct field name
            structured_portfolio.append({
                "asset_name": item.get("trading_symbol"),       # ← correct field name
                "isin": item.get("isin"),
                "asset_type": "Equity",                         # Holdings are always DEMAT equity
                "quantity": qty,
                "rate": avg_price,
                "total_value": round(qty * avg_price, 2),       # invested value (no live price here)
                # Settlement / pledge breakdown
                "t1_quantity": float(item.get("t1_quantity", 0)),
                "demat_free_quantity": float(item.get("demat_free_quantity", 0)),
                "pledge_quantity": float(item.get("pledge_quantity", 0)),
            })

        logger.info(f"Parsed {len(structured_portfolio)} holdings from Groww.")

        # ── 4. Intraday / carry-forward positions (CASH segment) ─────────────
        intraday_positions = []
        try:
            cash_pos_resp = groww.get_positions_for_user(
                segment=groww.SEGMENT_CASH,
                timeout=10,
            ) or {}
            intraday_positions = cash_pos_resp.get("positions", [])

            # Optionally fetch FNO positions if active
            active_segs = user_profile.get("active_segments", [])
            if "FNO" in active_segs:
                fno_resp = groww.get_positions_for_user(
                    segment=groww.SEGMENT_FNO,
                    timeout=10,
                ) or {}
                intraday_positions.extend(fno_resp.get("positions", []))

            logger.info(f"Fetched {len(intraday_positions)} open positions.")
        except Exception as e:
            logger.warning(f"get_positions_for_user failed: {e}")

        return {
            "status": "success",
            "source": "live_groww_api",
            "user_profile": user_profile,
            "available_cash": available_cash,
            "structured_portfolio": structured_portfolio,
            "intraday_positions": intraday_positions,
        }

    except ValueError as ve:
        # Missing credentials
        return {
            "error": str(ve),
            "structured_portfolio": [],
        }
    except Exception as e:
        logger.error(f"Groww API connection failed: {e}", exc_info=True)
        return {
            "error": f"Failed to sync with Groww API: {str(e)}. Ensure your token is fresh.",
            "structured_portfolio": [],
        }


def fetch_position_for_symbol(symbol: str) -> dict:
    """
    Fetch the current position for a single trading symbol (CASH segment).
    Useful for on-demand per-stock position queries from the AI agent.
    """
    try:
        groww = _build_groww_client()
        resp = groww.get_position_for_trading_symbol(
            trading_symbol=symbol.upper(),
            segment=groww.SEGMENT_CASH,
            timeout=10,
        ) or {}
        positions = resp.get("positions", [])
        if positions:
            return {"status": "success", "symbol": symbol.upper(), "position": positions[0]}
        return {"status": "no_position", "symbol": symbol.upper(), "position": None}
    except Exception as e:
        logger.error(f"get_position_for_trading_symbol({symbol}) failed: {e}")
        return {"error": str(e), "symbol": symbol.upper()}


def save_live_portfolio_to_cache(portfolio_data: list):
    """Saves the live portfolio to the cache file so the agent can quickly access it."""
    try:
        cache_file = "data/live_portfolio_structured.json"
        with open(cache_file, "w") as f:
            json.dump(portfolio_data, f, indent=2)
        logger.info(f"Live portfolio cached ({len(portfolio_data)} items) → {cache_file}")
    except Exception as e:
        logger.warning(f"Could not cache live portfolio: {e}")
