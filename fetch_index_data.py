from datetime import datetime, date, timedelta

import yfinance as yf

from config import NSELIB_INDEX_NAME, PRICE_HISTORY_DAYS, PRICE_HISTORY_PERIOD, INDEX_RETURN_TYPE
from data_store import DataStore
from models import FetchLog, FetchStatus, DataSource
from utils import setup_logger

logger = setup_logger(__name__, "fetch_index_data.log")

# Yahoo Finance symbol for Nifty 500
NIFTY500_YAHOO_SYMBOL = "^CRSLDX"


# nselib silently truncates any index_data response to ~70 rows regardless of
# the requested range (measured: 70 rows for a full-year query and for a
# 9-month query alike). Requesting 365-day chunks therefore yields a sparse,
# mostly-wrong benchmark. Chunk small enough to stay under the cap.
NSELIB_CHUNK_DAYS = 55
NSELIB_MAX_ROWS = 70

# Sanity floor for an index level. nselib returns a placeholder row with
# close=1.0 for dates the market was shut (e.g. 2025-10-22 Diwali,
# 2025-12-25 Christmas). Storing those injects a fake -99.99% day-over-day
# return into every relative-strength feature, so they are dropped at ingest.
MIN_VALID_INDEX_CLOSE = 100.0


def _plausible_index_row(close: float) -> bool:
    return close is not None and close >= MIN_VALID_INDEX_CLOSE


def fetch_via_nselib(start_date: date, end_date: date) -> list[dict]:
    """Try fetching index data from nselib in small chunks."""
    records: list[dict] = []
    try:
        from nselib import capital_market

        current_start = start_date
        while current_start < end_date:
            chunk_end = min(current_start + timedelta(days=NSELIB_CHUNK_DAYS), end_date)
            fmt_start = current_start.strftime("%d-%m-%Y")
            fmt_end = chunk_end.strftime("%d-%m-%Y")

            try:
                df = capital_market.index_data(
                    index=NSELIB_INDEX_NAME,
                    from_date=fmt_start,
                    to_date=fmt_end,
                )
            except Exception as e:
                logger.debug(f"nselib chunk {fmt_start}..{fmt_end} failed: {e}")
                current_start = chunk_end + timedelta(days=1)
                continue

            if df is not None and not df.empty:
                if len(df) >= NSELIB_MAX_ROWS:
                    logger.warning(
                        f"nselib chunk {fmt_start}..{fmt_end} hit the "
                        f"{NSELIB_MAX_ROWS}-row cap and may be truncated"
                    )
                for _, row in df.iterrows():
                    # nselib columns: TIMESTAMP, OPEN_INDEX_VAL, HIGH_INDEX_VAL,
                    # LOW_INDEX_VAL, CLOSE_INDEX_VAL, TRADED_QTY
                    raw_date = str(row.get("TIMESTAMP", ""))
                    try:
                        parsed_date = datetime.strptime(raw_date, "%d-%b-%Y").date()
                        date_str = parsed_date.isoformat()
                    except (ValueError, TypeError):
                        date_str = raw_date

                    close = float(row.get("CLOSE_INDEX_VAL", 0) or 0)
                    if not _plausible_index_row(close):
                        # Market was shut; nselib still emits a placeholder row.
                        continue
                    records.append(
                        {
                            "index_name": NSELIB_INDEX_NAME,
                            "date": date_str,
                            "open": float(row.get("OPEN_INDEX_VAL", 0) or 0),
                            "high": float(row.get("HIGH_INDEX_VAL", 0) or 0),
                            "low": float(row.get("LOW_INDEX_VAL", 0) or 0),
                            "close": close,
                            "volume": int(row.get("TRADED_QTY", 0) or 0),
                        }
                    )
            current_start = chunk_end + timedelta(days=1)

    except Exception as e:
        logger.warning(f"nselib index fetch failed: {e}")

    return records


def fetch_via_yfinance(period: str = PRICE_HISTORY_PERIOD) -> list[dict]:
    """Fallback: fetch Nifty 500 index data from Yahoo Finance."""
    records: list[dict] = []
    try:
        df = yf.download(NIFTY500_YAHOO_SYMBOL, period=period, progress=False)
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                dt = idx.date() if hasattr(idx, "date") else idx
                close = float(row.get("Close", 0))
                if not _plausible_index_row(close):
                    continue
                records.append(
                    {
                        "index_name": NSELIB_INDEX_NAME,
                        "date": str(dt),
                        "open": float(row.get("Open", 0)),
                        "high": float(row.get("High", 0)),
                        "low": float(row.get("Low", 0)),
                        "close": close,
                        "volume": int(row.get("Volume", 0)),
                    }
                )
    except Exception as e:
        logger.warning(f"yfinance index fetch failed: {e}")

    return records


def run(store: DataStore) -> dict:
    """Fetch Nifty 500 index-level OHLCV data."""
    started = datetime.now()
    logger.info("Fetching Nifty 500 index data...")

    end_date = date.today()
    # Match the stock history window. A 2y index against 5y of stock data
    # silently truncates every relative-strength calculation, because the
    # benchmark inner-joins onto the stock frame.
    start_date = end_date - timedelta(days=PRICE_HISTORY_DAYS)

    # Try nselib first
    records = fetch_via_nselib(start_date, end_date)
    source = DataSource.NSELIB

    # Fallback to yfinance
    if not records:
        logger.info("nselib returned no data, falling back to yfinance...")
        records = fetch_via_yfinance()
        source = DataSource.YFINANCE

    if records:
        count = store.upsert_index_data(records)
        logger.info(f"Stored {count} index data records")
    else:
        count = 0
        logger.warning("No index data fetched from any source")

    store.log_fetch(
        FetchLog(
            script_name="fetch_index_data",
            symbol=None,
            status=FetchStatus.SUCCESS if records else FetchStatus.FAILED,
            records_fetched=count,
            source=source,
            started_at=started,
            completed_at=datetime.now(),
        )
    )

    return {"records": count, "source": source.value}


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store)
        print(f"Done. {result['records']} index records from {result['source']}.")
    finally:
        store.close()
