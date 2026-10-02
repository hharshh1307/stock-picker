import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "stock_picker.db"

# yfinance settings
YFINANCE_BATCH_SIZE = 50
YFINANCE_BATCH_DELAY_SEC = 3.0
YFINANCE_RETRY_COUNT = 3
YFINANCE_RETRY_BACKOFF = 5.0
PRICE_HISTORY_PERIOD = "5y"
PRICE_HISTORY_INTERVAL = "1d"

# Tradability filter. Signals are only ever generated for names that could
# actually be bought or sold at a sane size — a momentum screen that surfaces an
# illiquid smallcap is a trap, not an opportunity. Thresholds are in rupees of
# average daily traded value over the lookback window.
MIN_AVG_TRADED_VALUE = 5_000_000   # Rs 5 crore/day
MIN_LIQUIDITY_LOOKBACK_DAYS = 90
MIN_LATEST_PRICE = 20.0            # Rs — filters out penny/penny-like stocks
MIN_PRICE_HISTORY_DAYS = 250       # need a year of history to score reliably

# Calendar days of price history to load for ML feature building. Keep in step
# with PRICE_HISTORY_PERIOD (5y ≈ 1825 calendar days, plus a small margin).
PRICE_HISTORY_DAYS = 1900

# Benchmark index. Prefer the dividend-reinvested series: comparing a
# total-return stock portfolio against a price-only index overstates alpha.
INDEX_PRIMARY = "Nifty 500 TRI"
INDEX_FALLBACK = "Nifty 500"

# Honest note on the benchmark: a true Nifty 500 Total Return index is not
# available from the free sources this project uses. Probed and confirmed to
# return no data: ^NIFTY500TR, ^CNXTR, ^NSE500, ^NSETR, 500TR.NS (yfinance) and
# "Nifty 500 TRI" / "Nifty 50 TRI" (nselib). Only the PRICE index is obtainable
# (^CRSLDX on yfinance, "Nifty 500" on nselib).
#
# Consequence: stock features use adj_close (dividends reinvested) while the
# benchmark uses a price-only close. That biases measured relative strength in
# the stock's favour by roughly the index dividend yield. This is surfaced in
# the admin health check rather than hidden, and is on the fix list for Phase 2
# (needs a licensed TRI feed or a dividend-yield adjustment).
INDEX_RETURN_TYPE = "price"  # not "total_return" — see note above

# Financials settings
FINANCIALS_BATCH_SIZE = 20
FINANCIALS_DELAY_SEC = 2.0

# News settings
GNEWS_DELAY_SEC = 5.0
GNEWS_MAX_RESULTS = 10
GNEWS_BATCH_SIZE = 10
GNEWS_LONG_PAUSE_SEC = 30.0

# RSS Feed URLs
RSS_FEEDS = {
    "economic_times_stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "economic_times_markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "moneycontrol_latest": "https://www.moneycontrol.com/rss/latestnews.xml",
    "moneycontrol_top": "https://www.moneycontrol.com/rss/MCtopnews.xml",
}

# nselib settings
NSELIB_INDEX_NAME = "Nifty 500"

# Index universe for the pipeline. Fetching every NSE-listed equity (~2,600
# names) multiplies yfinance load, takes over an hour to enrich, and floods the
# screen with microcaps that cannot be traded at size.
#
# All four are official NSE lists via nselib, together ~500 names (a
# Nifty-500-equivalent band). Do NOT re-add "nifty500" from the niftystocks
# package: that list is stale and still carries pre-merger tickers (LTI and
# MINDTREE rather than LTIM, HDFC rather than HDFCBANK, IDFC rather than
# IDFCFINBANK, TATAMOTORS rather than TMPV). Those symbols return zero price
# data forever. The nselib lists return the current names.
UNIVERSE_INDICES = ["nifty50", "niftynext50", "niftymidcap150", "niftysmallcap250"]

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global safeguard: pause after N consecutive failures
CONSECUTIVE_FAILURE_THRESHOLD = 3
CONSECUTIVE_FAILURE_PAUSE_SEC = 120.0
