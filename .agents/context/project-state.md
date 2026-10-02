# 📊 Project State Snapshot

> **Last Updated:** 2026-10-02
> **Updated By:** Antigravity (AI Assistant)

## Current Status: 🟡 Active Development — Phase 2 Partially Complete, 5-Month Gap

---

### What's Built

| Component | Status | Notes |
|---|---|---|
| Backend (FastAPI) | ✅ Built | 7 route groups: discovery, stocks, chat, user, signals, admin, auth |
| Frontend (Next.js 16) | ✅ Built | Discovery, chat, stock detail, portfolio, signals, admin, auth pages |
| Database (SQLite) | ✅ Active | `stock_picker.db` (~80MB), WAL mode |
| AI Agent (Gemini 2.5 Flash) | ⚠️ Built but GEMINI_API_KEY empty | ReAct loop, 13+ tools, SSE streaming |
| Discovery Engine | ✅ Working | 8 smart buckets, market pulse, sector grid, movers |
| Data Pipeline | ✅ Built | Stock list, prices (5yr), financials, news, index data |
| ML Pipeline | ✅ Built (v2) | 14 features, HistGradientBoosting, 3 horizons, time-split validation |
| Signal Engine | ✅ Built | RAG-style: ML retrieval → AI analysis → BUY/HOLD/SKIP |
| Price Scheduler | ✅ Built | APScheduler daily at 16:00 IST + startup staleness check |
| Groww Integration | ✅ Rewritten | TOTP auth, margin, positions, per-symbol lookup |
| Portfolio Analyzer | ✅ Built | P&L, diversification, concentration, sector allocation |
| Auth System | ✅ Built | Google OAuth + registration/login pages |
| Admin Dashboard | ✅ Built | Admin routes + frontend admin page |
| Backtester | ✅ Built | `backtester.py` |
| Audit Logger | ✅ Built | `audit_logger.py` |
| Alternative Assets | ✅ Built | `alternative_assets.py` |
| Deployment | ✅ Configured | Railway (backend), Vercel (frontend) |

---

### Uncommitted Changes (IMPORTANT)

**705 lines added across 13 files** — never committed. These appear to be a significant v2 upgrade:

| File | +Lines | What Changed |
|---|---|---|
| `config.py` | +45 | Liquidity filters, benchmark config, universe indices, price history tuning |
| `data_store.py` | +103 | New queries, schema additions |
| `fetch_nifty500_list.py` | +140 | Major rewrite — now uses 4 nselib indices instead of niftystocks |
| `ml_pipeline.py` | +129 | 14 features (was 8), time-based train/test split, regression + classification |
| `fetch_price_data.py` | +76 | Enhanced fetching |
| `price_scheduler.py` | +68 | More robust scheduling |
| `signal_engine.py` | +62 | Enhanced signal pipeline |
| `portfolio_analyzer.py` | +56 | Better P&L and analytics |
| `api_routes/admin.py` | +49 | Expanded admin capabilities |
| `fetch_index_data.py` | +65 | Better index data handling |
| `market_intelligence.py` | +12 | Minor enhancements |
| `render.yaml` | +2 | Config tweak |
| `requirements.txt` | +2 | Dependency update |

---

### Data Freshness

| Data Type | DB Size | Notes |
|---|---|---|
| Full database | ~80MB | `data/stock_picker.db` |
| ML predictions | 163KB | `data/ml_predictions.json` |
| OOT metrics | 787B | `data/oot_metrics.json` |
| ML models | Unknown | `data/ml_models/` directory |

> ⚠️ Exact data freshness unknown — run `uv run python main.py status` to check.

---

### Environment

- Python 3.12+, Node.js 18+
- LLM: **Gemini 2.5 Flash** (switched from GPT-4o) via OpenAI-compatible endpoint
- `.env` requires:
  ```
  GEMINI_API_KEY=...           # REQUIRED — currently empty!
  ADMIN_API_TOKEN=...          # Set to a random token
  GROWW_TOKEN=...              # Optional: Groww API key
  GROWW_API_SECRET=...         # Optional: Groww API secret
  GROWW_TOTP_SECRET=...        # Optional: TOTP for no-expiry auth
  ```
- Frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

### Known Issues

- [ ] `GEMINI_API_KEY` empty in `.env` — AI agent non-functional
- [ ] 705 lines of uncommitted changes at risk of loss
- [ ] XIRR / time-weighted returns not implemented
- [ ] Dividend income not tracked
- [ ] Agent conversation memory not persisted across sessions
- [ ] No automated test suite
- [ ] No API input validation (Pydantic models)
- [ ] No error boundaries on frontend
- [ ] Financial JSON key normalization incomplete
- [ ] Nifty 500 TRI (Total Return Index) not available from free sources — price-only benchmark used

---

### Recent History

- (2026-10-02) Memory files updated — 5-month gap since last session
- (2026-05-01) Agent memory + NVIDIA skills integration
- (2026-04-29) Groww integration full rewrite, agent tools updated
- (2026-04-27) Alternative assets support added
- (2026-04-22) ML pipeline, backtester, audit logger added
- (2026-04-21) Phase 1 complete, `.agents/` system created
- (2026-04-20) Project created, first commit
