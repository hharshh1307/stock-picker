import json
import sqlite3
from datetime import date, datetime
from typing import Optional

from config import DB_PATH, DATA_DIR
from models import (
    Stock,
    PriceRecord,
    QuarterlyFinancial,
    NewsArticle,
    FetchLog,
    FetchStatus,
    AssetType,
    UserProfile,
    InvestmentPlan,
    PortfolioItem,
)
from utils import setup_logger

logger = setup_logger(__name__)


def _safe_get(row: sqlite3.Row, key: str, default=None):
    """Safely get a value from sqlite3.Row, which doesn't support .get()."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY,
    yahoo_symbol TEXT NOT NULL,
    company_name TEXT NOT NULL,
    asset_type TEXT DEFAULT 'stock',
    sector TEXT,
    industry TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    adj_close REAL NOT NULL,
    volume INTEGER NOT NULL,
    source TEXT DEFAULT 'yfinance',
    UNIQUE(symbol, date),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, date);

CREATE TABLE IF NOT EXISTS quarterly_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period_ending DATE NOT NULL,
    statement_type TEXT NOT NULL CHECK(statement_type IN ('income', 'balance_sheet', 'cashflow')),
    data_json TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, period_ending, statement_type),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);
CREATE INDEX IF NOT EXISTS idx_financials_symbol ON quarterly_financials(symbol);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source_name TEXT NOT NULL,
    published_at TIMESTAMP,
    description TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, url),
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);
CREATE INDEX IF NOT EXISTS idx_news_symbol ON news(symbol);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);

CREATE TABLE IF NOT EXISTS index_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_name TEXT NOT NULL DEFAULT 'Nifty 500',
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(index_name, date)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_name TEXT NOT NULL,
    symbol TEXT,
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'partial', 'skipped')),
    records_fetched INTEGER DEFAULT 0,
    error_message TEXT,
    source TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fetch_log_script ON fetch_log(script_name, started_at);

CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_tolerance TEXT NOT NULL,
    total_capital REAL NOT NULL,
    expected_returns REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frequency TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_buy_price REAL NOT NULL,
    strategy_frequency TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);
"""


class DataStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = str(db_path or DB_PATH)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        self.initialize_schema()

    def initialize_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add columns that may be missing from older databases."""
        try:
            self.conn.execute("SELECT asset_type FROM stocks LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Migrating stocks table: adding asset_type column")
            self.conn.execute("ALTER TABLE stocks ADD COLUMN asset_type TEXT DEFAULT 'stock'")
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- Stocks ---

    def upsert_stocks(self, stocks: list[Stock]) -> int:
        count = 0
        for s in stocks:
            self.conn.execute(
                """INSERT INTO stocks (symbol, yahoo_symbol, company_name, asset_type, sector, industry, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(symbol) DO UPDATE SET
                     yahoo_symbol=excluded.yahoo_symbol,
                     company_name=excluded.company_name,
                     asset_type=excluded.asset_type,
                     sector=excluded.sector,
                     industry=excluded.industry,
                     last_updated=excluded.last_updated""",
                (s.symbol, s.yahoo_symbol, s.company_name, s.asset_type.value, s.sector, s.industry,
                 s.last_updated or datetime.now()),
            )
            count += 1
        self.conn.commit()
        return count

    def get_all_stocks(self) -> list[Stock]:
        rows = self.conn.execute("SELECT * FROM stocks ORDER BY symbol").fetchall()
        return [
            Stock(
                symbol=r["symbol"],
                yahoo_symbol=r["yahoo_symbol"],
                company_name=r["company_name"],
                asset_type=AssetType(_safe_get(r, "asset_type", "stock")),
                sector=r["sector"],
                industry=r["industry"],
                last_updated=r["last_updated"],
            )
            for r in rows
        ]

    def get_stock(self, symbol: str) -> Optional[Stock]:
        r = self.conn.execute("SELECT * FROM stocks WHERE symbol = ?", (symbol,)).fetchone()
        if not r:
            return None
        return Stock(
            symbol=r["symbol"],
            yahoo_symbol=r["yahoo_symbol"],
            company_name=r["company_name"],
            asset_type=AssetType(_safe_get(r, "asset_type", "stock")),
            sector=r["sector"],
            industry=r["industry"],
            last_updated=r["last_updated"],
        )

    # --- Prices ---

    def upsert_prices(self, prices: list[PriceRecord]) -> int:
        import math
        count = 0
        for p in prices:
            # Skip records with missing close price (yfinance returns NaN for incomplete data)
            if p.close is None or (isinstance(p.close, float) and math.isnan(p.close)):
                continue
            self.conn.execute(
                """INSERT INTO prices (symbol, date, open, high, low, close, adj_close, volume, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(symbol, date) DO UPDATE SET
                     open=excluded.open, high=excluded.high, low=excluded.low,
                     close=excluded.close, adj_close=excluded.adj_close,
                     volume=excluded.volume, source=excluded.source""",
                (p.symbol, p.date.isoformat(), p.open, p.high, p.low, p.close,
                 p.adj_close, p.volume, p.source),
            )
            count += 1
        self.conn.commit()
        return count

    def get_prices(self, symbol: str, start_date: date, end_date: date) -> list[PriceRecord]:
        rows = self.conn.execute(
            "SELECT * FROM prices WHERE symbol = ? AND date BETWEEN ? AND ? ORDER BY date",
            (symbol, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
        return [
            PriceRecord(
                symbol=r["symbol"],
                date=date.fromisoformat(r["date"]),
                open=r["open"],
                high=r["high"],
                low=r["low"],
                close=r["close"],
                adj_close=r["adj_close"],
                volume=r["volume"],
                source=r["source"],
            )
            for r in rows
        ]

    def get_latest_price_date(self, symbol: str) -> Optional[date]:
        row = self.conn.execute(
            "SELECT MAX(date) as max_date FROM prices WHERE symbol = ?", (symbol,)
        ).fetchone()
        if row and row["max_date"]:
            return date.fromisoformat(row["max_date"])
        return None

    # --- Financials ---

    def upsert_financials(self, financials: list[QuarterlyFinancial]) -> int:
        count = 0
        for f in financials:
            self.conn.execute(
                """INSERT INTO quarterly_financials (symbol, period_ending, statement_type, data_json, fetched_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(symbol, period_ending, statement_type) DO UPDATE SET
                     data_json=excluded.data_json, fetched_at=excluded.fetched_at""",
                (f.symbol, f.period_ending.isoformat(), f.statement_type, f.data_json,
                 f.fetched_at or datetime.now()),
            )
            count += 1
        self.conn.commit()
        return count

    def get_financials(self, symbol: str, statement_type: Optional[str] = None) -> list[QuarterlyFinancial]:
        if statement_type:
            rows = self.conn.execute(
                "SELECT * FROM quarterly_financials WHERE symbol = ? AND statement_type = ? ORDER BY period_ending DESC",
                (symbol, statement_type),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM quarterly_financials WHERE symbol = ? ORDER BY period_ending DESC",
                (symbol,),
            ).fetchall()
        return [
            QuarterlyFinancial(
                symbol=r["symbol"],
                period_ending=date.fromisoformat(r["period_ending"]),
                statement_type=r["statement_type"],
                data_json=r["data_json"],
                fetched_at=r["fetched_at"],
            )
            for r in rows
        ]

    # --- News ---

    def upsert_news(self, articles: list[NewsArticle]) -> int:
        count = 0
        for a in articles:
            try:
                self.conn.execute(
                    """INSERT INTO news (symbol, title, url, source_name, published_at, description, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(symbol, url) DO NOTHING""",
                    (a.symbol, a.title, a.url, a.source_name,
                     a.published_at.isoformat() if a.published_at else None,
                     a.description, a.fetched_at or datetime.now()),
                )
                count += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return count

    def get_news(self, symbol: str, limit: int = 20) -> list[NewsArticle]:
        rows = self.conn.execute(
            "SELECT * FROM news WHERE symbol = ? ORDER BY published_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
        return [
            NewsArticle(
                symbol=r["symbol"],
                title=r["title"],
                url=r["url"],
                source_name=r["source_name"],
                published_at=r["published_at"],
                description=r["description"],
                fetched_at=r["fetched_at"],
            )
            for r in rows
        ]

    # --- Index data ---

    def upsert_index_data(self, records: list[dict]) -> int:
        count = 0
        for r in records:
            self.conn.execute(
                """INSERT INTO index_data (index_name, date, open, high, low, close, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(index_name, date) DO UPDATE SET
                     open=excluded.open, high=excluded.high, low=excluded.low,
                     close=excluded.close, volume=excluded.volume""",
                (r["index_name"], r["date"], r.get("open"), r.get("high"),
                 r.get("low"), r.get("close"), r.get("volume")),
            )
            count += 1
        self.conn.commit()
        return count

    # --- Fetch log ---

    def log_fetch(self, log: FetchLog) -> None:
        self.conn.execute(
            """INSERT INTO fetch_log (script_name, symbol, status, records_fetched, error_message, source, started_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log.script_name, log.symbol, log.status.value, log.records_fetched,
             log.error_message, log.source.value if log.source else None,
             log.started_at, log.completed_at or datetime.now()),
        )
        self.conn.commit()

    def get_pipeline_status(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT script_name,
                      MAX(started_at) as last_run,
                      SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                      SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed_count,
                      SUM(records_fetched) as total_records
               FROM fetch_log
               GROUP BY script_name
               ORDER BY last_run DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stocks_by_sector(self, sector: str) -> list[Stock]:
        rows = self.conn.execute(
            "SELECT * FROM stocks WHERE sector = ? ORDER BY symbol", (sector,)
        ).fetchall()
        return [
            Stock(
                symbol=r["symbol"],
                yahoo_symbol=r["yahoo_symbol"],
                company_name=r["company_name"],
                asset_type=AssetType(_safe_get(r, "asset_type", "stock")),
                sector=r["sector"],
                industry=r["industry"],
                last_updated=r["last_updated"],
            )
            for r in rows
        ]

    def get_all_sectors(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT sector, COUNT(*) as stock_count
               FROM stocks WHERE sector IS NOT NULL
               GROUP BY sector ORDER BY stock_count DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_table_counts(self) -> dict[str, int]:
        tables = ["stocks", "prices", "quarterly_financials", "news", "index_data", "portfolio_items"]
        counts = {}
        for t in tables:
            row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
            counts[t] = row["cnt"]
        return counts

    # --- Discovery & API methods ---

    def search_stocks(self, query: str, limit: int = 20) -> list[Stock]:
        """Search stocks by symbol or company name (case-insensitive)."""
        pattern = f"%{query}%"
        rows = self.conn.execute(
            """SELECT * FROM stocks
               WHERE symbol LIKE ? OR company_name LIKE ?
               ORDER BY
                 CASE WHEN symbol LIKE ? THEN 0 ELSE 1 END,
                 symbol
               LIMIT ?""",
            (pattern, pattern, f"{query}%", limit),
        ).fetchall()
        return [
            Stock(
                symbol=r["symbol"],
                yahoo_symbol=r["yahoo_symbol"],
                company_name=r["company_name"],
                asset_type=AssetType(_safe_get(r, "asset_type", "stock")),
                sector=r["sector"],
                industry=r["industry"],
                last_updated=r["last_updated"],
            )
            for r in rows
        ]

    def get_stock_detail(self, symbol: str) -> Optional[dict]:
        """Get comprehensive stock detail including latest price and 52-week range."""
        stock = self.get_stock(symbol)
        if not stock:
            return None

        # Get latest price
        latest = self.conn.execute(
            "SELECT * FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (symbol,),
        ).fetchone()

        # Get 52-week high/low
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=365)).isoformat()
        range_52w = self.conn.execute(
            """SELECT MIN(low) as low_52w, MAX(high) as high_52w
               FROM prices WHERE symbol = ? AND date >= ?""",
            (symbol, cutoff),
        ).fetchone()

        # Get YTD return
        ytd_start = f"{date.today().year}-01-01"
        ytd_row = self.conn.execute(
            """SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1""",
            (symbol, ytd_start),
        ).fetchone()

        ytd_return = None
        if ytd_row and latest and ytd_row["close"] > 0:
            ytd_return = ((latest["close"] - ytd_row["close"]) / ytd_row["close"]) * 100

        return {
            "symbol": stock.symbol,
            "yahoo_symbol": stock.yahoo_symbol,
            "company_name": stock.company_name,
            "asset_type": stock.asset_type.value,
            "sector": stock.sector,
            "industry": stock.industry,
            "latest_price": latest["close"] if latest else None,
            "latest_date": latest["date"] if latest else None,
            "open": latest["open"] if latest else None,
            "high": latest["high"] if latest else None,
            "low": latest["low"] if latest else None,
            "volume": latest["volume"] if latest else None,
            "high_52w": range_52w["high_52w"] if range_52w else None,
            "low_52w": range_52w["low_52w"] if range_52w else None,
            "ytd_return": round(ytd_return, 2) if ytd_return is not None else None,
        }

    def get_price_series(self, symbol: str, days: int = 365) -> list[dict]:
        """Get price series for charting."""
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        rows = self.conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM prices WHERE symbol = ? AND date >= ?
               ORDER BY date ASC""",
            (symbol, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_financials_summary(self, symbol: str) -> list[dict]:
        """Get summarized quarterly financials for display."""
        import json
        rows = self.conn.execute(
            """SELECT period_ending, statement_type, data_json
               FROM quarterly_financials
               WHERE symbol = ?
               ORDER BY period_ending DESC, statement_type""",
            (symbol,),
        ).fetchall()

        # Group by period and extract key metrics
        from collections import defaultdict
        by_period: dict = defaultdict(dict)
        for r in rows:
            period = r["period_ending"]
            stmt_type = r["statement_type"]
            data = json.loads(r["data_json"])
            by_period[period][stmt_type] = data

        results = []
        for period, statements in sorted(by_period.items(), reverse=True):
            income = statements.get("income", {})
            balance = statements.get("balance_sheet", {})
            cashflow = statements.get("cashflow", {})

            results.append({
                "period": period,
                "revenue": income.get("Total Revenue") or income.get("Operating Revenue"),
                "net_income": income.get("Net Income") or income.get("Net Income From Continuing Operation Net Minority Interest"),
                "ebitda": income.get("Normalized EBITDA") or income.get("EBITDA"),
                "total_assets": balance.get("Total Assets"),
                "total_debt": balance.get("Total Debt"),
                "total_equity": balance.get("Total Equity Gross Minority Interest"),
                "operating_cashflow": cashflow.get("Operating Cash Flow"),
                "free_cashflow": cashflow.get("Free Cash Flow"),
            })

        return results[:8]  # Last 8 quarters

    def get_market_news(self, limit: int = 20) -> list[dict]:
        """Get general market news (not tied to specific stock)."""
        rows = self.conn.execute(
            """SELECT title, url, source_name, published_at, description
               FROM news WHERE symbol = '_MARKET'
               ORDER BY published_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stock_news(self, symbol: str, limit: int = 20) -> list[dict]:
        """Get news for a specific stock."""
        rows = self.conn.execute(
            """SELECT title, url, source_name, published_at, description
               FROM news WHERE symbol = ?
               ORDER BY published_at DESC LIMIT ?""",
            (symbol, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Portfolio & Investment Plans ---

    def get_user_profile(self) -> Optional[UserProfile]:
        r = self.conn.execute("SELECT * FROM user_profiles ORDER BY id LIMIT 1").fetchone()
        if not r:
            return None
        return UserProfile(
            id=r["id"],
            risk_tolerance=r["risk_tolerance"],
            total_capital=r["total_capital"],
            expected_returns=r["expected_returns"]
        )

    def upsert_user_profile(self, profile: UserProfile) -> None:
        self.conn.execute("DELETE FROM user_profiles")
        self.conn.execute(
            """INSERT INTO user_profiles (risk_tolerance, total_capital, expected_returns)
               VALUES (?, ?, ?)""",
            (profile.risk_tolerance, profile.total_capital, profile.expected_returns)
        )
        self.conn.commit()

    def get_investment_plans(self) -> list[InvestmentPlan]:
        rows = self.conn.execute("SELECT * FROM investment_plans ORDER BY id").fetchall()
        return [
            InvestmentPlan(
                id=r["id"],
                frequency=r["frequency"],
                allocated_amount=r["allocated_amount"],
                description=r["description"]
            )
            for r in rows
        ]

    def upsert_investment_plan(self, plan: InvestmentPlan) -> None:
        if plan.id:
            self.conn.execute(
                """UPDATE investment_plans SET frequency=?, allocated_amount=?, description=? WHERE id=?""",
                (plan.frequency, plan.allocated_amount, plan.description, plan.id)
            )
        else:
            self.conn.execute(
                """INSERT INTO investment_plans (frequency, allocated_amount, description) VALUES (?, ?, ?)""",
                (plan.frequency, plan.allocated_amount, plan.description)
            )
        self.conn.commit()

    def delete_investment_plan(self, plan_id: int) -> None:
        self.conn.execute("DELETE FROM investment_plans WHERE id=?", (plan_id,))
        self.conn.commit()

    def get_portfolio_items(self) -> list[PortfolioItem]:
        rows = self.conn.execute("SELECT * FROM portfolio_items ORDER BY id").fetchall()
        return [
            PortfolioItem(
                id=r["id"],
                symbol=r["symbol"],
                quantity=r["quantity"],
                average_buy_price=r["average_buy_price"],
                strategy_frequency=r["strategy_frequency"],
                added_at=datetime.fromisoformat(r["added_at"]) if isinstance(r["added_at"], str) else r["added_at"]
            )
            for r in rows
        ]

    def upsert_portfolio_item(self, item: PortfolioItem) -> None:
        if item.id:
            self.conn.execute(
                """UPDATE portfolio_items SET symbol=?, quantity=?, average_buy_price=?, strategy_frequency=? WHERE id=?""",
                (item.symbol, item.quantity, item.average_buy_price, item.strategy_frequency, item.id)
            )
        else:
            self.conn.execute(
                """INSERT INTO portfolio_items (symbol, quantity, average_buy_price, strategy_frequency, added_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item.symbol, item.quantity, item.average_buy_price, item.strategy_frequency, item.added_at.isoformat())
            )
        self.conn.commit()

    def delete_portfolio_item(self, item_id: int) -> None:
        self.conn.execute("DELETE FROM portfolio_items WHERE id=?", (item_id,))
        self.conn.commit()
