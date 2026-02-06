import math
import time
import random
from datetime import datetime, date, timedelta

import pandas as pd
import yfinance as yf

from config import (
    YFINANCE_BATCH_SIZE,
    YFINANCE_BATCH_DELAY_SEC,
    YFINANCE_RETRY_COUNT,
    YFINANCE_RETRY_BACKOFF,
    PRICE_HISTORY_PERIOD,
    PRICE_HISTORY_INTERVAL,
    CONSECUTIVE_FAILURE_THRESHOLD,
    CONSECUTIVE_FAILURE_PAUSE_SEC,
)
from data_store import DataStore
from models import PriceRecord, FetchLog, FetchStatus, DataSource
from utils import setup_logger

logger = setup_logger(__name__, "fetch_price_data.log")


def download_batch(
    yahoo_symbols: list[str],
    start: str | None = None,
    end: str | None = None,
    period: str | None = None,
) -> pd.DataFrame:
    """Download OHLCV for a batch of tickers via yfinance."""
    kwargs: dict = {
        "tickers": " ".join(yahoo_symbols),
        "interval": PRICE_HISTORY_INTERVAL,
        "auto_adjust": False,
        "progress": False,
    }
    if start and end:
        kwargs["start"] = start
        kwargs["end"] = end
    else:
        kwargs["period"] = period or PRICE_HISTORY_PERIOD

    return yf.download(**kwargs)


def parse_price_df(df: pd.DataFrame, symbol: str, yahoo_symbol: str) -> list[PriceRecord]:
    """Convert a yfinance DataFrame into PriceRecord objects for a single ticker."""
    records: list[PriceRecord] = []
    if df.empty:
        return records

    # For multi-ticker downloads, columns are MultiIndex (Price, Ticker)
    # For single-ticker downloads, columns are flat
    if isinstance(df.columns, pd.MultiIndex):
        try:
            ticker_df = df.xs(yahoo_symbol, level="Ticker", axis=1)
        except KeyError:
            return records
    else:
        ticker_df = df

    for idx, row in ticker_df.iterrows():
        try:
            dt = idx.date() if hasattr(idx, "date") else idx
            records.append(
                PriceRecord(
                    symbol=symbol,
                    date=dt,
                    open=float(row.get("Open", 0)),
                    high=float(row.get("High", 0)),
                    low=float(row.get("Low", 0)),
                    close=float(row.get("Close", 0)),
                    adj_close=float(row.get("Adj Close", row.get("Close", 0))),
                    volume=int(row.get("Volume", 0)),
                )
            )
        except (ValueError, TypeError) as e:
            continue

    return records


def run(
    store: DataStore,
    symbols: list[str] | None = None,
    full_refresh: bool = False,
) -> dict:
    """Fetch OHLCV price data for all stocks.

    Args:
        store: DataStore instance
        symbols: Optional list of NSE symbols to fetch. If None, fetches all from DB.
        full_refresh: If True, re-fetch all history. If False, incremental from last date.
    """
    started = datetime.now()
    all_stocks = store.get_all_stocks()
    if not all_stocks:
        logger.error("No stocks in database. Run fetch_nifty500_list first.")
        return {"error": "No stocks in database"}

    if symbols:
        stock_map = {s.symbol: s for s in all_stocks}
        stocks = [stock_map[sym] for sym in symbols if sym in stock_map]
    else:
        stocks = all_stocks

    logger.info(f"Fetching prices for {len(stocks)} stocks (full_refresh={full_refresh})")

    yahoo_symbols = [s.yahoo_symbol for s in stocks]
    symbol_lookup = {s.yahoo_symbol: s.symbol for s in stocks}

    total_records = 0
    success_count = 0
    failed_tickers: list[str] = []
    consecutive_failures = 0

    # Process in batches
    num_batches = math.ceil(len(yahoo_symbols) / YFINANCE_BATCH_SIZE)
    for batch_idx in range(num_batches):
        start_idx = batch_idx * YFINANCE_BATCH_SIZE
        batch = yahoo_symbols[start_idx : start_idx + YFINANCE_BATCH_SIZE]
        logger.info(f"Batch {batch_idx + 1}/{num_batches}: {len(batch)} tickers")

        # Determine date range for this batch
        # For simplicity in batch mode, use the same period for all tickers in the batch
        try:
            df = download_batch(batch, period=PRICE_HISTORY_PERIOD)
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1} download failed: {e}")
            failed_tickers.extend([symbol_lookup.get(y, y) for y in batch])
            consecutive_failures += 1
            if consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                logger.warning(
                    f"{consecutive_failures} consecutive batch failures. "
                    f"Pausing {CONSECUTIVE_FAILURE_PAUSE_SEC}s..."
                )
                time.sleep(CONSECUTIVE_FAILURE_PAUSE_SEC)
                consecutive_failures = 0
            continue

        consecutive_failures = 0

        # Parse each ticker's data from the batch result
        for yahoo_sym in batch:
            nse_sym = symbol_lookup.get(yahoo_sym, yahoo_sym.replace(".NS", ""))
            records = parse_price_df(df, nse_sym, yahoo_sym)
            if records:
                # If incremental, filter out dates we already have
                if not full_refresh:
                    latest = store.get_latest_price_date(nse_sym)
                    if latest:
                        records = [r for r in records if r.date > latest]

                if records:
                    inserted = store.upsert_prices(records)
                    total_records += inserted
                    success_count += 1
                else:
                    success_count += 1  # Already up to date
            else:
                failed_tickers.append(nse_sym)

        # Delay between batches
        if batch_idx < num_batches - 1:
            delay = random.uniform(
                YFINANCE_BATCH_DELAY_SEC, YFINANCE_BATCH_DELAY_SEC * 2
            )
            logger.debug(f"Sleeping {delay:.1f}s between batches...")
            time.sleep(delay)

    # Log summary
    logger.info(
        f"=== fetch_price_data Summary ===\n"
        f"  Total stocks: {len(stocks)}\n"
        f"  Successful: {success_count}\n"
        f"  Failed: {len(failed_tickers)}\n"
        f"  Records inserted: {total_records}\n"
        f"  Duration: {datetime.now() - started}"
    )
    if failed_tickers:
        logger.warning(f"  Failed tickers: {failed_tickers[:20]}")

    store.log_fetch(
        FetchLog(
            script_name="fetch_price_data",
            symbol=None,
            status=FetchStatus.SUCCESS if not failed_tickers else FetchStatus.PARTIAL,
            records_fetched=total_records,
            error_message=f"Failed: {failed_tickers[:20]}" if failed_tickers else None,
            source=DataSource.YFINANCE,
            started_at=started,
            completed_at=datetime.now(),
        )
    )

    return {
        "total": len(stocks),
        "success": success_count,
        "failed": len(failed_tickers),
        "records": total_records,
        "failed_tickers": failed_tickers,
    }


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store)
        print(
            f"Done. {result['success']}/{result['total']} stocks, "
            f"{result['records']} price records."
        )
    finally:
        store.close()
