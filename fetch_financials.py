import json
import time
from datetime import datetime

import yfinance as yf

from config import (
    FINANCIALS_BATCH_SIZE,
    FINANCIALS_DELAY_SEC,
    CONSECUTIVE_FAILURE_THRESHOLD,
    CONSECUTIVE_FAILURE_PAUSE_SEC,
)
from data_store import DataStore
from models import QuarterlyFinancial, FetchLog, FetchStatus, DataSource
from utils import setup_logger, RateLimiter

logger = setup_logger(__name__, "fetch_financials.log")


STATEMENT_TYPES = {
    "income": "quarterly_income_stmt",
    "balance_sheet": "quarterly_balance_sheet",
    "cashflow": "quarterly_cashflow",
}


def fetch_for_ticker(yahoo_symbol: str, nse_symbol: str) -> list[QuarterlyFinancial]:
    """Fetch all quarterly financial statements for a single ticker."""
    records: list[QuarterlyFinancial] = []
    ticker = yf.Ticker(yahoo_symbol)

    for stmt_type, attr_name in STATEMENT_TYPES.items():
        try:
            df = getattr(ticker, attr_name, None)
            if df is None or df.empty:
                continue

            # Columns are quarter-end dates, rows are line items
            for col in df.columns:
                period_date = col.date() if hasattr(col, "date") else col
                # Convert the column to a JSON-serializable dict
                col_data = df[col].dropna()
                data_dict = {}
                for idx_label, val in col_data.items():
                    key = str(idx_label)
                    try:
                        data_dict[key] = float(val)
                    except (ValueError, TypeError):
                        data_dict[key] = str(val)

                if data_dict:
                    records.append(
                        QuarterlyFinancial(
                            symbol=nse_symbol,
                            period_ending=period_date,
                            statement_type=stmt_type,
                            data_json=json.dumps(data_dict),
                            fetched_at=datetime.now(),
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch {stmt_type} for {nse_symbol}: {e}")

    return records


def run(
    store: DataStore,
    symbols: list[str] | None = None,
    statement_type: str | None = None,
) -> dict:
    """Fetch quarterly financials for all stocks.

    Args:
        store: DataStore instance
        symbols: Optional list of NSE symbols. If None, fetches all from DB.
        statement_type: Optional filter (income, balance_sheet, cashflow).
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

    logger.info(f"Fetching quarterly financials for {len(stocks)} stocks")

    rate_limiter = RateLimiter(min_delay=FINANCIALS_DELAY_SEC, max_delay=FINANCIALS_DELAY_SEC + 1.0)
    total_records = 0
    success_count = 0
    empty_count = 0
    failed_tickers: list[str] = []
    consecutive_failures = 0

    for i, stock in enumerate(stocks):
        rate_limiter.wait()

        try:
            records = fetch_for_ticker(stock.yahoo_symbol, stock.symbol)
            if statement_type:
                records = [r for r in records if r.statement_type == statement_type]

            if records:
                inserted = store.upsert_financials(records)
                total_records += inserted
                success_count += 1
                consecutive_failures = 0
            else:
                empty_count += 1
                consecutive_failures = 0
                logger.debug(f"No quarterly data for {stock.symbol}")

        except Exception as e:
            logger.warning(f"Failed to fetch financials for {stock.symbol}: {e}")
            failed_tickers.append(stock.symbol)
            consecutive_failures += 1
            if consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                logger.warning(
                    f"{consecutive_failures} consecutive failures. "
                    f"Pausing {CONSECUTIVE_FAILURE_PAUSE_SEC}s..."
                )
                time.sleep(CONSECUTIVE_FAILURE_PAUSE_SEC)
                consecutive_failures = 0

        # Batch pause every FINANCIALS_BATCH_SIZE tickers
        if (i + 1) % FINANCIALS_BATCH_SIZE == 0:
            logger.info(f"Progress: {i + 1}/{len(stocks)} stocks processed")
            time.sleep(10.0)

    logger.info(
        f"=== fetch_financials Summary ===\n"
        f"  Total stocks: {len(stocks)}\n"
        f"  With data: {success_count}\n"
        f"  Empty (no data): {empty_count}\n"
        f"  Failed: {len(failed_tickers)}\n"
        f"  Records inserted: {total_records}\n"
        f"  Duration: {datetime.now() - started}"
    )
    if failed_tickers:
        logger.warning(f"  Failed tickers: {failed_tickers[:20]}")

    store.log_fetch(
        FetchLog(
            script_name="fetch_financials",
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
        "with_data": success_count,
        "empty": empty_count,
        "failed": len(failed_tickers),
        "records": total_records,
    }


if __name__ == "__main__":
    store = DataStore()
    try:
        result = run(store)
        print(
            f"Done. {result['with_data']}/{result['total']} stocks with data, "
            f"{result['records']} financial records."
        )
    finally:
        store.close()
