# 🏛️ System Architecture

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts | Deployed on Vercel |
| **Backend** | Python 3.12+, FastAPI, uvicorn | Deployed on Railway |
| **Database** | SQLite (WAL mode) | `data/stock_picker.db` (~80MB) |
| **AI/LLM** | Gemini 2.5 Flash via OpenAI-compatible API | ReAct agent with tool calling |
| **ML** | scikit-learn HistGradientBoosting (regression + classification) | 14 features, 3 horizons |
| **Data Sources** | yfinance, GNews API, RSS feeds (ET, MoneyControl), nselib | Free/low-cost |
| **Broker** | Groww API (read-only, TOTP-capable) | Live portfolio sync |
| **Package Manager** | uv (Python), npm (Node.js) | |
| **Deployment** | Railway (backend), Vercel (frontend) | |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16)                     │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────────┐  │
│  │Discovery │ │  Chat    │ │ Stock   │ │ Portfolio/     │  │
│  │  Page    │ │  Page    │ │ Detail  │ │ Signals/Admin  │  │
│  └────┬─────┘ └────┬─────┘ └────┬────┘ └──────┬─────────┘  │
│       └─────────────┴────────────┴──────────────┘           │
│                         │ API calls                          │
│  ┌─────────────────────────────────────┐                     │
│  │ Auth: Google OAuth + Login/Register │                     │
│  └─────────────────────────────────────┘                     │
└─────────────────────────┼────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │   BACKEND (FastAPI)    │
              │                        │
              │  /api/discovery/*      │
              │  /api/stocks/*         │
              │  /api/chat (SSE)       │
              │  /api/user/*           │
              │  /api/signals/*        │
              │  /api/admin/*          │
              │  /api/auth/*           │
              │                        │
              │  ┌──────────────────┐  │
              │  │  AI Agent        │  │
              │  │  (ReAct Loop)    │  │
              │  │  13+ tools       │  │
              │  │  Gemini 2.5 Flash│  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Signal Engine    │  │
              │  │ ML → AI → Signal │  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Discovery Engine │  │
              │  │ 8 smart buckets  │  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Portfolio Analyzer│  │
              │  │ P&L, risk, alloc │  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Price Scheduler  │  │
              │  │ APScheduler 16:00│  │
              │  └──────────────────┘  │
              └───────────┬────────────┘
                          │
              ┌───────────┴───────────┐
              │   DATA LAYER           │
              │                        │
              │  SQLite (WAL mode)     │
              │  ┌──────────────────┐  │
              │  │ stocks (~500)    │  │
              │  │ prices (5yr)     │  │
              │  │ financials (qtly)│  │
              │  │ news             │  │
              │  │ index_data       │  │
              │  │ user_profiles    │  │
              │  │ investment_plans │  │
              │  │ portfolio_items  │  │
              │  │ signal_*         │  │
              │  │ fetch_log        │  │
              │  │ users            │  │
              │  └──────────────────┘  │
              │                        │
              │  ML Models (joblib)    │
              │  ┌──────────────────┐  │
              │  │ data/ml_models/  │  │
              │  │ ml_predictions   │  │
              │  │ oot_metrics      │  │
              │  └──────────────────┘  │
              └───────────┬────────────┘
                          │
              ┌───────────┴───────────┐
              │   DATA PIPELINE        │
              │                        │
              │  fetch_nifty500_list   │
              │  fetch_price_data      │
              │  fetch_financials      │
              │  fetch_news            │
              │  fetch_index_data      │
              │  market_intelligence   │
              │  ml_pipeline           │
              │  signal_engine         │
              └────────────────────────┘
```

## Key File Map

### Backend (Python)
| File | Purpose | Size |
|------|---------|------|
| `main.py` | CLI entry point (argparse), pipeline orchestration | 9KB |
| `api_server.py` | FastAPI app, CORS, router mounting, lifespan | 4KB |
| `api_routes/*.py` | 7 API endpoint groups (discovery, stocks, chat, user, signals, admin, auth) | ~53KB |
| `data_store.py` | SQLite DAL — all queries, schema, migrations | 33KB |
| `discovery_engine.py` | 8 stock buckets computation | 24KB |
| `market_intelligence.py` | Market breadth, sectors, movers, volume analysis | 20KB |
| `agent.py` | FinancialExpertAgent — ReAct loop with Gemini | 19KB |
| `agent_tools.py` | 13+ tool definitions with OpenAI function schemas | 45KB |
| `agent_prompts.py` | System prompt for "Nifty Sage" persona | 10KB |
| `signal_engine.py` | RAG-style signal pipeline (ML → AI → BUY/HOLD/SKIP) | 22KB |
| `ml_pipeline.py` | 14-feature ML models, 3 horizons, time-split | 22KB |
| `portfolio_analyzer.py` | P&L, diversification, concentration, sector allocation | 25KB |
| `groww_integration.py` | Groww broker API (TOTP auth, holdings, positions, margin) | 9KB |
| `price_scheduler.py` | APScheduler daily refresh at 16:00 IST | 11KB |
| `backtester.py` | Signal performance backtesting | 7KB |
| `audit_logger.py` | Chat audit trail | 4KB |
| `intent_classifier.py` | User intent classification for agent routing | 10KB |
| `embedding_search.py` | Semantic search over stock data | 7KB |
| `screener_scraper.py` | Screener.in data scraping | 15KB |
| `alternative_assets.py` | Multi-asset support (beyond stocks) | 5KB |
| `models.py` | Dataclasses: Asset, PriceRecord, Financial, Portfolio | 2KB |
| `config.py` | Paths, batch sizes, delays, thresholds, universe config | 4KB |
| `fetch_*.py` | Data pipeline scripts (list, prices, financials, news, index) | ~40KB |

### Frontend (Next.js)
| Path | Purpose |
|------|---------|
| `web/src/app/page.tsx` | Discovery page (home) |
| `web/src/app/chat/` | AI chat interface |
| `web/src/app/stock/` | Stock detail page |
| `web/src/app/portfolio/` | Portfolio management |
| `web/src/app/signals/` | ML signal display |
| `web/src/app/admin/` | Admin dashboard |
| `web/src/app/login/` | Login page |
| `web/src/app/register/` | Registration page |
| `web/src/app/settings/` | User profile & investment plans |
| `web/src/components/discovery/` | Market pulse, sector grid, buckets, movers |
| `web/src/components/chat/` | Chat UI components |
| `web/src/components/layout/` | Navigation, layout shells |
| `web/src/components/stock/` | Stock detail components |
| `web/src/components/shared/` | Shared components |
| `web/src/components/ui/` | shadcn/ui primitives |
| `web/src/lib/` | API client, types, utilities |
| `web/src/middleware.ts` | Auth middleware |

## Database Schema (SQLite)

### Core Tables
- **stocks** — ~500 Nifty stocks (symbol PK, yahoo_symbol, company_name, asset_type, sector, industry)
- **prices** — Daily OHLCV (symbol+date unique, 5 years history)
- **quarterly_financials** — Income, balance sheet, cashflow (JSON blobs per quarter)
- **news** — Stock-specific + market news (symbol+url unique)
- **index_data** — Nifty 500 index daily data

### User Tables
- **users** — Auth users (Google OAuth + local registration)
- **user_profiles** — Risk tolerance, total capital, expected returns
- **investment_plans** — Frequency-based plans (Daily/Weekly/Monthly/Yearly/Long-term)
- **portfolio_items** — Holdings (symbol, quantity, avg_buy_price, strategy_frequency)

### Signal Tables
- **signal_candidates** — ML-retrieved top-K candidates per frequency
- **signal_decisions** — AI agent BUY/HOLD/SKIP decisions
- **signal_outcomes** — Actual returns after holding period (back-filled)

### System Tables
- **fetch_log** — Pipeline execution audit trail

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/discovery/market-pulse` | Market breadth & sentiment |
| GET | `/api/discovery/sectors` | Sector performance grid |
| GET | `/api/discovery/buckets` | 8 smart stock buckets |
| GET | `/api/discovery/movers` | Top gainers/losers |
| GET | `/api/stocks/search?q=` | Stock search |
| GET | `/api/stocks/{symbol}` | Stock detail |
| GET | `/api/stocks/{symbol}/prices` | Price history |
| GET | `/api/stocks/{symbol}/financials` | Financial summaries |
| POST | `/api/chat` | AI chat (SSE streaming) |
| GET | `/api/user/profile` | Get user profile |
| PUT | `/api/user/profile` | Update user profile |
| GET | `/api/user/plans` | Get investment plans |
| POST | `/api/user/plans` | Create/update plan |
| GET | `/api/user/portfolio` | Get portfolio items |
| POST | `/api/user/portfolio` | Add portfolio item |
| GET | `/api/signals/*` | ML signal endpoints |
| GET | `/api/admin/*` | Admin dashboard data |
| POST | `/api/auth/*` | Auth (login, register, OAuth) |
