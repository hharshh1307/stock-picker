# 📁 Codebase Map

> Quick reference for what each file does. Consult this before modifying anything.

## Backend (Python — project root)

### Entry Points
| File | What It Does |
|------|-------------|
| `main.py` | CLI entry: `list`, `prices`, `financials`, `news`, `index`, `serve`, `chat`, `status`, `all` |
| `api_server.py` | FastAPI app factory, CORS config, router mounting, lifespan management |

### Core Logic
| File | What It Does |
|------|-------------|
| `data_store.py` | SQLite DAL — schema creation, migrations, all CRUD operations. **The single source of truth for DB access.** |
| `discovery_engine.py` | Computes 8 stock discovery buckets from local data (momentum, beaten down, volume surge, revenue rockets, profit machines, 52w high/low, sector outperformers) |
| `market_intelligence.py` | Market breadth, sector performance, top movers, volume spikes, financial highlights |
| `agent.py` | `FinancialExpertAgent` class — ReAct loop, tool execution, conversation memory, tiktoken summarization |
| `agent_tools.py` | 13 tool definitions + implementations (search, info, prices, financials, sector, movers, breadth, volume, news, compare, valuation, web_search) |
| `agent_prompts.py` | System prompt builder for "Nifty Sage" — dynamic context injection (stock count, portfolio, plans) |
| `chat.py` | CLI REPL interface for agent |

### Data Pipeline
| File | What It Does |
|------|-------------|
| `fetch_nifty500_list.py` | Fetches Nifty 500 constituents from nselib, enriches with yfinance (sector/industry) |
| `fetch_price_data.py` | Batch fetches 2yr OHLCV from yfinance with retry logic |
| `fetch_financials.py` | Fetches quarterly income/balance/cashflow from yfinance |
| `fetch_news.py` | Fetches stock news from GNews API + RSS feeds (ET, MoneyControl) |
| `fetch_index_data.py` | Fetches Nifty 500 index data from nselib |

### Config & Models
| File | What It Does |
|------|-------------|
| `config.py` | Paths (DB, data, logs), batch sizes, delays, thresholds |
| `models.py` | Dataclasses: Asset/Stock, PriceRecord, QuarterlyFinancial, NewsArticle, FetchLog, UserProfile, InvestmentPlan, PortfolioItem |
| `utils.py` | Logger setup utility |
| `ticker_mapping.py` | NSE → Yahoo symbol mapping helpers |

### API Routes
| File | Endpoints |
|------|-----------|
| `api_routes/discovery.py` | Market pulse, sectors, buckets, movers |
| `api_routes/stocks.py` | Search, detail, prices, financials |
| `api_routes/chat.py` | POST /chat with SSE streaming |
| `api_routes/user.py` | Profile, plans, portfolio CRUD |

## Frontend (Next.js — `web/`)

### Pages (App Router)
| Path | What It Does |
|------|-------------|
| `src/app/page.tsx` | Discovery page — server component, fetches all discovery data |
| `src/app/chat/` | AI chat interface |
| `src/app/stock/[symbol]/` | Individual stock detail page |
| `src/app/portfolio/` | Portfolio management UI |
| `src/app/settings/` | User profile & investment plans configuration |
| `src/app/layout.tsx` | Root layout with navigation |
| `src/app/globals.css` | Global styles & CSS variables |

### Components
| Directory | Contains |
|-----------|----------|
| `src/components/discovery/` | MarketPulseCard, SectorGrid, BucketCarousel, MoversTable |
| `src/components/chat/` | Chat UI (messages, input, streaming indicators) |
| `src/components/layout/` | Navigation, sidebar, page shells |
| `src/components/shared/` | Reusable components (sparklines, badges, etc.) |
| `src/components/ui/` | shadcn/ui primitives (button, card, input, etc.) |

### Lib
| File | What It Does |
|------|-------------|
| `src/lib/api.ts` | API client — typed fetch wrappers for all backend endpoints |
| `src/lib/types.ts` | TypeScript interfaces matching all API response shapes |
| `src/lib/utils.ts` | cn() utility for className merging |

## Config Files
| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project config (uv) |
| `requirements.txt` | Python dependencies |
| `web/package.json` | Node.js dependencies |
| `web/tsconfig.json` | TypeScript config |
| `web/next.config.ts` | Next.js config |
| `web/components.json` | shadcn/ui config |
| `.env` / `.env.example` | Backend environment variables |
| `web/.env.example` | Frontend environment variables |
| `railway.json` | Railway deployment config |
| `render.yaml` | Render deployment config |
| `nixpacks.toml` | Nixpacks build config (Railway) |
| `web/vercel.json` | Vercel deployment config |
