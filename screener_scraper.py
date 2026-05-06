"""
Screener.in scraper — fetches rich fundamental data that Yahoo Finance misses.

Data extracted per stock:
- Market cap, PE, PB, dividend yield, face value
- ROE, ROCE (3-year averages)  
- Promoter/FII/DII/Public shareholding %
- Quarterly P&L: Sales, Expenses, Net Profit (last 8 quarters)
- Annual P&L: Sales, Net Profit (last 5 years)
- Balance sheet: Reserves, Borrowings, Fixed Assets, Working Capital
- Cash flow: Operating, Investing, Financing
- Key ratios: Debt/Equity, Interest Coverage, Asset Turnover, Current Ratio
- Peer comparison table

All data cached in SQLite for offline use.
"""

import json
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from data_store import DataStore
from utils import setup_logger

logger = setup_logger(__name__, "screener.log")

SCREENER_BASE = "https://www.screener.in/company"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.screener.in/",
}
REQUEST_DELAY = 1.5  # seconds between requests — be a good citizen


def _get_soup(url: str, retries: int = 2) -> Optional[BeautifulSoup]:
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            elif r.status_code == 404:
                return None
            else:
                logger.warning(f"HTTP {r.status_code} for {url}")
        except Exception as e:
            logger.warning(f"Request failed (attempt {attempt+1}): {e}")
            time.sleep(2)
    return None


def _parse_number(text: str) -> Optional[float]:
    """Parse Indian number format: '1,23,456.78' or '1,234 Cr' → float."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace("₹", "").replace("%", "").strip()
    # Remove suffixes
    multiplier = 1
    if text.endswith(" Cr"):
        text = text[:-3].strip()
        multiplier = 1  # already in Crores
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def _parse_ratio_table(soup: BeautifulSoup) -> dict[str, Any]:
    """Extract the key ratios section (PE, PB, ROE, ROCE, etc.)."""
    result = {}
    # The top ratios are in <li> elements inside #top-ratios
    top_ratios = soup.find(id="top-ratios")
    if not top_ratios:
        return result

    for li in top_ratios.find_all("li"):
        name_el = li.find("span", class_="name")
        value_el = li.find("span", class_="number")
        if name_el and value_el:
            name = name_el.get_text(strip=True)
            value_text = value_el.get_text(strip=True)
            value = _parse_number(value_text)
            # Map to clean keys
            key_map = {
                "Market Cap": "market_cap_cr",
                "Current Price": "current_price",
                "High / Low": None,  # skip
                "Stock P/E": "pe_ratio",
                "Book Value": "book_value",
                "Dividend Yield": "dividend_yield_pct",
                "ROCE": "roce_pct",
                "ROE": "roe_pct",
                "Face Value": "face_value",
            }
            key = key_map.get(name)
            if key and value is not None:
                result[key] = value
            elif name == "High / Low":
                # Parse high/low separately
                parts = value_text.split("/")
                if len(parts) == 2:
                    result["high_52w"] = _parse_number(parts[0])
                    result["low_52w"] = _parse_number(parts[1])

    return result


def _parse_shareholding(soup: BeautifulSoup) -> dict[str, Any]:
    """Extract latest promoter/FII/DII/Public holding percentages."""
    result = {}
    section = soup.find(id="shareholding")
    if not section:
        return result

    table = section.find("table")
    if not table:
        return result

    rows = table.find_all("tr")
    if not rows:
        return result

    # Get latest quarter column (first data column after header)
    for row in rows:
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True).lower()
        value_text = cells[1].get_text(strip=True)  # Most recent quarter
        value = _parse_number(value_text)

        if "promoter" in label:
            result["promoter_holding_pct"] = value
        elif "fii" in label or "foreign" in label:
            result["fii_holding_pct"] = value
        elif "dii" in label or "domestic" in label:
            result["dii_holding_pct"] = value
        elif "public" in label:
            result["public_holding_pct"] = value

    return result


def _parse_data_table(section) -> list[dict]:
    """
    Parse a Screener data table (quarterly results, P&L, balance sheet, etc.)
    Returns list of {label: str, values: [float|None, ...], periods: [str, ...]}
    """
    if not section:
        return []

    table = section.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    # First row = headers (periods)
    header_cells = rows[0].find_all(["th", "td"])
    periods = [c.get_text(strip=True) for c in header_cells[1:]]  # skip "Row Name" cell

    result = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        values = [_parse_number(c.get_text(strip=True)) for c in cells[1:]]
        if label and any(v is not None for v in values):
            result.append({
                "label": label,
                "periods": periods,
                "values": values,
            })

    return result


def _parse_peer_comparison(soup: BeautifulSoup) -> list[dict]:
    """Extract peer comparison table."""
    result = []
    section = soup.find(id="peers")
    if not section:
        return result

    table = section.find("table")
    if not table:
        return result

    rows = table.find_all("tr")
    if len(rows) < 2:
        return result

    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]

    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        peer = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                peer[headers[i]] = cell.get_text(strip=True)
        if peer:
            result.append(peer)

    return result[:10]  # Top 10 peers


def scrape_screener(symbol: str, consolidated: bool = True) -> dict[str, Any]:
    """
    Scrape Screener.in for rich fundamental data for a stock.
    
    Returns a dict with:
    - ratios: PE, PB, ROCE, ROE, Market Cap, etc.
    - shareholding: promoter/FII/DII/public %
    - quarterly_pl: last 8 quarters Sales, Expenses, Net Profit
    - annual_pl: last 5 years
    - balance_sheet: Borrowings, Reserves, Fixed Assets
    - cash_flow: Operating, Investing, Financing
    - peers: peer comparison table
    - pros: list of positive highlights
    - cons: list of negative highlights
    """
    variant = "consolidated" if consolidated else "standalone"
    url = f"{SCREENER_BASE}/{symbol.upper()}/{variant}/"
    
    logger.info(f"Scraping Screener.in: {url}")
    soup = _get_soup(url)
    
    if not soup:
        # Try standalone if consolidated 404s
        if consolidated:
            url = f"{SCREENER_BASE}/{symbol.upper()}/standalone/"
            soup = _get_soup(url)
        if not soup:
            return {"error": f"Stock {symbol} not found on Screener.in", "symbol": symbol}

    result: dict[str, Any] = {
        "symbol": symbol.upper(),
        "scraped_at": datetime.now().isoformat(),
        "url": url,
    }

    # Company name
    name_el = soup.find("h1", class_="company-name") or soup.find("h1")
    if name_el:
        result["company_name"] = name_el.get_text(strip=True)

    # Key ratios
    result["ratios"] = _parse_ratio_table(soup)

    # Pros & Cons (Screener's own analysis)
    pros_section = soup.find("div", class_="pros")
    cons_section = soup.find("div", class_="cons")
    if pros_section:
        result["pros"] = [li.get_text(strip=True) for li in pros_section.find_all("li")]
    if cons_section:
        result["cons"] = [li.get_text(strip=True) for li in cons_section.find_all("li")]

    # Shareholding
    result["shareholding"] = _parse_shareholding(soup)

    # Quarterly results
    q_section = soup.find(id="quarters")
    result["quarterly_pl"] = _parse_data_table(q_section)

    # Annual P&L
    pl_section = soup.find(id="profit-loss")
    result["annual_pl"] = _parse_data_table(pl_section)

    # Balance sheet
    bs_section = soup.find(id="balance-sheet")
    result["balance_sheet"] = _parse_data_table(bs_section)

    # Cash flow
    cf_section = soup.find(id="cash-flow")
    result["cash_flow"] = _parse_data_table(cf_section)

    # Ratios over time (Screener's ratio table)
    ratios_section = soup.find(id="ratios")
    result["ratios_history"] = _parse_data_table(ratios_section)

    # Peer comparison
    result["peers"] = _parse_peer_comparison(soup)

    return result


def get_screener_data(symbol: str, store: DataStore, max_age_hours: int = 24) -> dict[str, Any]:
    """
    Get Screener data for a symbol, using SQLite cache to avoid re-scraping.
    Cache expires after max_age_hours (default: 24h).
    """
    # Ensure cache table exists
    store.conn.execute("""
        CREATE TABLE IF NOT EXISTS screener_cache (
            symbol TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    store.conn.commit()

    # Check cache
    row = store.conn.execute(
        "SELECT data_json, fetched_at FROM screener_cache WHERE symbol = ?",
        (symbol.upper(),),
    ).fetchone()

    if row:
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if datetime.now() - fetched_at < timedelta(hours=max_age_hours):
            return json.loads(row["data_json"])

    # Cache miss or expired — scrape
    time.sleep(REQUEST_DELAY)  # Be polite
    data = scrape_screener(symbol)

    if "error" not in data:
        store.conn.execute(
            """INSERT OR REPLACE INTO screener_cache (symbol, data_json, fetched_at)
               VALUES (?, ?, ?)""",
            (symbol.upper(), json.dumps(data), datetime.now().isoformat()),
        )
        store.conn.commit()

    return data


def format_screener_for_agent(data: dict) -> str:
    """
    Format scraped Screener data into a compact, agent-readable text block.
    Keeps only the highest-signal data to not bloat the context window.
    """
    if "error" in data:
        return f"Screener data unavailable: {data['error']}"

    lines = []
    sym = data.get("symbol", "")
    name = data.get("company_name", sym)
    lines.append(f"## {name} ({sym}) — Screener.in Data")

    # Key ratios
    r = data.get("ratios", {})
    if r:
        lines.append("\n**Key Ratios:**")
        if r.get("market_cap_cr"):
            lines.append(f"- Market Cap: ₹{r['market_cap_cr']:,.0f} Cr")
        if r.get("pe_ratio"):
            lines.append(f"- P/E: {r['pe_ratio']:.1f}x")
        if r.get("book_value"):
            lines.append(f"- Book Value: ₹{r['book_value']:.2f}")
        if r.get("roe_pct"):
            lines.append(f"- ROE: {r['roe_pct']:.1f}%")
        if r.get("roce_pct"):
            lines.append(f"- ROCE: {r['roce_pct']:.1f}%")
        if r.get("dividend_yield_pct"):
            lines.append(f"- Dividend Yield: {r['dividend_yield_pct']:.2f}%")

    # Shareholding
    sh = data.get("shareholding", {})
    if sh:
        lines.append("\n**Shareholding (Latest):**")
        if sh.get("promoter_holding_pct") is not None:
            lines.append(f"- Promoter: {sh['promoter_holding_pct']:.1f}%")
        if sh.get("fii_holding_pct") is not None:
            lines.append(f"- FII: {sh['fii_holding_pct']:.1f}%")
        if sh.get("dii_holding_pct") is not None:
            lines.append(f"- DII: {sh['dii_holding_pct']:.1f}%")
        if sh.get("public_holding_pct") is not None:
            lines.append(f"- Public: {sh['public_holding_pct']:.1f}%")

    # Screener's own pros/cons (very high signal)
    if data.get("pros"):
        lines.append("\n**Screener Pros:**")
        for p in data["pros"][:4]:
            lines.append(f"✅ {p}")
    if data.get("cons"):
        lines.append("\n**Screener Cons:**")
        for c in data["cons"][:4]:
            lines.append(f"⚠️ {c}")

    # Latest quarterly P&L (last 4 quarters)
    qpl = data.get("quarterly_pl", [])
    if qpl:
        lines.append("\n**Quarterly P&L (₹ Cr):**")
        key_rows = ["Sales", "Net Profit", "OPM %"]
        for row in qpl:
            if any(k.lower() in row["label"].lower() for k in key_rows):
                periods = row["periods"][-4:]
                values = row["values"][-4:]
                vals_str = " | ".join(
                    f"{v:,.0f}" if v is not None else "—" for v in values
                )
                lines.append(f"- {row['label']}: {vals_str}  [{' | '.join(periods)}]")

    # Annual P&L trend (last 5 years)
    apl = data.get("annual_pl", [])
    if apl:
        lines.append("\n**Annual P&L (₹ Cr):**")
        for row in apl:
            if any(k.lower() in row["label"].lower() for k in ["Sales", "Net Profit"]):
                periods = row["periods"][-5:]
                values = row["values"][-5:]
                vals_str = " | ".join(
                    f"{v:,.0f}" if v is not None else "—" for v in values
                )
                lines.append(f"- {row['label']}: {vals_str}  [{' | '.join(periods)}]")

    # Peer comparison (first 5 peers, key columns only)
    peers = data.get("peers", [])
    if peers:
        lines.append("\n**Peer Comparison:**")
        key_cols = ["Name", "CMP", "P/E", "Mar Cap", "ROE", "ROCE"]
        for peer in peers[:5]:
            parts = []
            for col in key_cols:
                val = peer.get(col, peer.get(col.lower()))
                if val:
                    parts.append(f"{col}={val}")
            if parts:
                lines.append(f"- {' | '.join(parts)}")

    return "\n".join(lines)
