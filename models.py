from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional


class FetchStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class DataSource(Enum):
    YFINANCE = "yfinance"
    GNEWS = "gnews"
    RSS_FEED = "rss_feed"
    NSELIB = "nselib"
    NIFTYSTOCKS = "niftystocks"


class AssetType(Enum):
    STOCK = "stock"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    INDEX = "index"


@dataclass
class Asset:
    symbol: str
    yahoo_symbol: str
    company_name: str
    asset_type: AssetType = AssetType.STOCK
    sector: Optional[str] = None
    industry: Optional[str] = None
    last_updated: Optional[datetime] = None


# Alias for backward compatibility during transition
Stock = Asset

@dataclass
class PriceRecord:
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int
    source: str = "yfinance"


@dataclass
class QuarterlyFinancial:
    symbol: str
    period_ending: date
    statement_type: str  # "income", "balance_sheet", "cashflow"
    data_json: str
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class NewsArticle:
    symbol: str
    title: str
    url: str
    source_name: str
    published_at: Optional[datetime] = None
    description: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class FetchLog:
    script_name: str
    symbol: Optional[str]
    status: FetchStatus
    records_fetched: int = 0
    error_message: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    source: Optional[DataSource] = None


@dataclass
class UserProfile:
    id: Optional[int]
    risk_tolerance: str  # 'low', 'medium', 'high'
    total_capital: float
    expected_returns: float


@dataclass
class InvestmentPlan:
    id: Optional[int]
    frequency: str  # 'Daily', 'Weekly', 'Monthly', 'Yearly', 'Long-term'
    allocated_amount: float
    description: Optional[str] = None


@dataclass
class PortfolioItem:
    id: Optional[int]
    symbol: str
    quantity: float
    average_buy_price: float
    strategy_frequency: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
