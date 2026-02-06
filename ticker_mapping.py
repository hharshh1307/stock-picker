# Known NSE symbol -> Yahoo Finance symbol overrides.
# Default rule: symbol + ".NS" (e.g. RELIANCE -> RELIANCE.NS)
# Add entries here when a symbol doesn't follow that convention.
SYMBOL_OVERRIDES: dict[str, str] = {
    "M&M": "M&M.NS",
    "M&MFIN": "M&MFIN.NS",
    "L&TFH": "L&TFH.NS",
    "ABORTIONCLEARLY": "",  # placeholder removed; add real overrides as discovered
}

# Remove placeholder
SYMBOL_OVERRIDES = {k: v for k, v in SYMBOL_OVERRIDES.items() if v}


def nse_to_yahoo(symbol: str) -> str:
    if symbol in SYMBOL_OVERRIDES:
        return SYMBOL_OVERRIDES[symbol]
    return f"{symbol}.NS"


def yahoo_to_nse(yahoo_symbol: str) -> str:
    for nse, yahoo in SYMBOL_OVERRIDES.items():
        if yahoo == yahoo_symbol:
            return nse
    return yahoo_symbol.replace(".NS", "")
