# 📊 Data Dictionary

## Database: `data/stock_picker.db` (SQLite, WAL mode)

---

### `stocks` — Master stock list
| Column | Type | Key | Description |
|--------|------|-----|-------------|
| symbol | TEXT | PK | NSE symbol (e.g., "RELIANCE") |
| yahoo_symbol | TEXT | NOT NULL | Yahoo Finance ticker (e.g., "RELIANCE.NS") |
| company_name | TEXT | NOT NULL | Full company name |
| asset_type | TEXT | DEFAULT 'stock' | Enum: stock, mutual_fund, etf, index |
| sector | TEXT | | One of ~11 sectors |
| industry | TEXT | | Sub-industry classification |
| last_updated | TIMESTAMP | | Last enrichment timestamp |

**Sectors in data:** Financial Services, Information Technology, Consumer Discretionary, Industrials, Consumer Staples, Materials, Energy, Health Care, Communication Services, Utilities, Real Estate

---

### `prices` — Daily OHLCV price data
| Column | Type | Key | Description |
|--------|------|-----|-------------|
| id | INTEGER | PK (auto) | |
| symbol | TEXT | FK → stocks | |
| date | DATE | UNIQUE(symbol,date) | Trading date |
| open | REAL | | Opening price (INR) |
| high | REAL | | Day high |
| low | REAL | | Day low |
| close | REAL | | Closing price |
| adj_close | REAL | | Adjusted close (splits/dividends) |
| volume | INTEGER | | Trading volume |
| source | TEXT | DEFAULT 'yfinance' | Data source |

**Coverage:** ~2 years of daily data per stock
**Index:** `idx_prices_symbol_date` on (symbol, date)

---

### `quarterly_financials` — Financial statements
| Column | Type | Key | Description |
|--------|------|-----|-------------|
| id | INTEGER | PK (auto) | |
| symbol | TEXT | FK → stocks | |
| period_ending | DATE | UNIQUE(symbol,period,type) | Quarter end date |
| statement_type | TEXT | CHECK | "income", "balance_sheet", or "cashflow" |
| data_json | TEXT | | Full statement as JSON blob |
| fetched_at | TIMESTAMP | | When fetched |

**Key fields in data_json (income):** Total Revenue, Operating Revenue, Net Income, EBITDA, Normalized EBITDA
**Key fields in data_json (balance_sheet):** Total Assets, Total Debt, Total Equity Gross Minority Interest
**Key fields in data_json (cashflow):** Operating Cash Flow, Free Cash Flow
**Index:** `idx_financials_symbol` on (symbol)

---

### `news` — Stock-specific and market news
| Column | Type | Key | Description |
|--------|------|-----|-------------|
| id | INTEGER | PK (auto) | |
| symbol | TEXT | FK → stocks | "_MARKET" for general market news |
| title | TEXT | | Headline |
| url | TEXT | UNIQUE(symbol,url) | Article URL |
| source_name | TEXT | | "GNews", "EconomicTimes", etc. |
| published_at | TIMESTAMP | | Publication date |
| description | TEXT | | Article summary/snippet |
| fetched_at | TIMESTAMP | | When fetched |

**Sources:** GNews API (stock-specific), RSS feeds (Economic Times, MoneyControl)
**Indexes:** `idx_news_symbol`, `idx_news_published`

---

### `index_data` — Nifty 500 index daily data
| Column | Type | Key | Description |
|--------|------|-----|-------------|
| id | INTEGER | PK (auto) | |
| index_name | TEXT | DEFAULT 'Nifty 500' | |
| date | DATE | UNIQUE(index,date) | |
| open/high/low/close | REAL | | Index OHLC values |
| volume | INTEGER | | |

---

### `user_profiles` — User financial profile (single user)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| risk_tolerance | TEXT | "low", "medium", "high" |
| total_capital | REAL | Total investable capital (INR) |
| expected_returns | REAL | Target annual return % |

---

### `investment_plans` — Frequency-based investment allocations
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| frequency | TEXT | "Daily", "Weekly", "Monthly", "Yearly", "Long-term" |
| allocated_amount | REAL | Amount per frequency period (INR) |
| description | TEXT | User notes/label for the plan |

---

### `portfolio_items` — User's stock holdings
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| symbol | TEXT | FK → stocks |
| quantity | REAL | Number of shares/units |
| average_buy_price | REAL | Average cost basis (INR) |
| strategy_frequency | TEXT | Linked to plan frequency |
| added_at | TIMESTAMP | When added |

---

### `fetch_log` — Data pipeline audit trail
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| script_name | TEXT | e.g., "fetch_price_data" |
| symbol | TEXT | Specific stock (nullable for batch ops) |
| status | TEXT | "success", "failed", "partial", "skipped" |
| records_fetched | INTEGER | Number of records inserted |
| error_message | TEXT | Error details if failed |
| source | TEXT | "yfinance", "gnews", "rss_feed", etc. |
| started_at | TIMESTAMP | Pipeline start time |
| completed_at | TIMESTAMP | Pipeline end time |

---

## Data Quality Notes

### Known Issues
- **Financials coverage**: Not all 500 stocks have quarterly financials (some fail yfinance fetch)
- **News freshness**: GNews has rate limits; RSS feeds are general market only
- **Volume data**: Some stocks have 0 volume days (thinly traded small caps)
- **Yahoo symbol mapping**: `.NS` suffix convention; some stocks may have mapping issues
- **JSON schema**: Financial statement JSON keys vary by company (not all have "Total Revenue")

### Data Refresh Commands
```bash
uv run python main.py all              # Full pipeline (takes ~30-60 min)
uv run python main.py prices           # Just prices
uv run python main.py financials       # Just financials
uv run python main.py news             # Just news
uv run python main.py status           # Check pipeline status
```
