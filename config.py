from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "stock_picker.db"

# yfinance settings
YFINANCE_BATCH_SIZE = 50
YFINANCE_BATCH_DELAY_SEC = 3.0
YFINANCE_RETRY_COUNT = 3
YFINANCE_RETRY_BACKOFF = 5.0
PRICE_HISTORY_PERIOD = "2y"
PRICE_HISTORY_INTERVAL = "1d"

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

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global safeguard: pause after N consecutive failures
CONSECUTIVE_FAILURE_THRESHOLD = 3
CONSECUTIVE_FAILURE_PAUSE_SEC = 120.0
