# 🏛️ System Architecture

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts | Deployed on Vercel |
| **Backend** | Python 3.12+, FastAPI, uvicorn | Deployed on Railway |
| **Database** | SQLite (WAL mode) | `data/stock_picker.db` (~41MB) |
| **AI/LLM** | OpenAI GPT-4o (primary), GPT-4o-mini (fallback) | ReAct agent with tool calling |
| **Data Sources** | yfinance, GNews API, RSS feeds (ET, MoneyControl), nselib | Free/low-cost |
| **Package Manager** | uv (Python), npm (Node.js) | |
| **Deployment** | Railway (backend), Vercel (frontend) | |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16)                 │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────┐  │
│  │Discovery │ │  Chat    │ │ Stock   │ │ Portfolio  │  │
│  │  Page    │ │  Page    │ │ Detail  │ │ & Settings │  │
│  └────┬─────┘ └────┬─────┘ └────┬────┘ └─────┬──────┘  │
│       └─────────────┴────────────┴─────────────┘        │
│                         │ API calls                      │
└─────────────────────────┼───────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │   BACKEND (FastAPI)    │
              │                        │
              │  /api/discovery/*      │
              │  /api/stocks/*         │
              │  /api/chat (SSE)       │
              │  /api/user/*           │
              │                        │
              │  ┌──────────────────┐  │
              │  │  AI Agent        │  │
              │  │  (ReAct Loop)    │  │
              │  │  13 tools        │  │
              │  │  GPT-4o          │  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │ Discovery Engine │  │
              │  │ 8 smart buckets  │  │
              │  └──────────────────┘  │
              │                        │
              │  ┌──────────────────┐  │
              │  │  Market Intel    │  │
              │  │  Breadth/Sectors │  │
              │  └──────────────────┘  │
              └───────────┬────────────┘
                          │
              ┌───────────┴───────────┐
              │   DATA LAYER           │
              │                        │
              │  SQLite (WAL mode)     │
              │  ┌──────────────────┐  │
              │  │ stocks (500)     │  │
              │  │ prices (2yr)     │  │
              │  │ financials (qtly)│  │
              │  │ news             │  │
              │  │ index_data       │  │
              │  │ user_profiles    │  │
              │  │ investment_plans │  │
              │  │ portfolio_items  │  │
              │  │ fetch_log        │  │
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
              └────────────────────────┘
```

## Key File Map

### Backend (Python)
| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | CLI entry point (argparse), pipeline orchestration | 235 |
| `api_server.py` | FastAPI app, CORS, router mounting | 113 |
| `api_routes/*.py` | API endpoint handlers (discovery, stocks, chat, user) | ~13K |
| `data_store.py` | SQLite DAL — all queries, schema, migrations | 645 |
| `discovery_engine.py` | 8 stock buckets computation | 611 |
| `market_intelligence.py` | Market breadth, sectors, movers, volume analysis | ~500 |
| `agent.py` | FinancialExpertAgent — ReAct loop with tool calling | ~250 |
| `agent_tools.py` | 13 tool definitions with OpenAI function schemas | ~700 |
| `agent_prompts.py` | System prompt for "Nifty Sage" persona | 142 |
| `models.py` | Dataclasses: Asset, PriceRecord, Financial, Portfolio, etc. | 112 |
| `config.py` | Paths, batch sizes, delays, thresholds | 45 |
| `fetch_*.py` | Data pipeline scripts (list, prices, financials, news, index) | ~30K |

### Frontend (Next.js)
| Path | Purpose |
|------|---------|
| `web/src/app/page.tsx` | Discovery page (server component) |
| `web/src/app/chat/` | AI chat interface |
| `web/src/app/stock/` | Stock detail page |
| `web/src/app/portfolio/` | Portfolio management |
| `web/src/app/settings/` | User profile & investment plans |
| `web/src/components/discovery/` | Market pulse, sector grid, buckets, movers |
| `web/src/components/chat/` | Chat UI components |
| `web/src/components/layout/` | Navigation, layout shells |
| `web/src/components/ui/` | shadcn/ui primitives |
| `web/src/lib/api.ts` | API client (fetch wrapper) |
| `web/src/lib/types.ts` | TypeScript interfaces for all API responses |
| `web/src/lib/utils.ts` | Utility functions |

## Database Schema (SQLite)

### Core Tables
- **stocks** — 500 Nifty stocks (symbol PK, yahoo_symbol, company_name, asset_type, sector, industry)
- **prices** — Daily OHLCV (symbol+date unique, 2 years history)
- **quarterly_financials** — Income, balance sheet, cashflow (JSON blobs per quarter)
- **news** — Stock-specific + market news (symbol+url unique)
- **index_data** — Nifty 500 index daily data

### User Tables
- **user_profiles** — Risk tolerance, total capital, expected returns (single row)
- **investment_plans** — Frequency-based plans (Daily/Weekly/Monthly/Yearly/Long-term)
- **portfolio_items** — Holdings (symbol, quantity, avg_buy_price, strategy_frequency)

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
