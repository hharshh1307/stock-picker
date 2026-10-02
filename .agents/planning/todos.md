# ✅ Active TODOs

> All active tasks across agents. Update status as work progresses.
> Mark with: `[ ]` not started, `[~]` in progress, `[x]` done

---

## Immediate — Housekeeping

- [ ] **Commit 705 lines of pending changes** — Major v2 upgrade sitting uncommitted
- [ ] **Set `GEMINI_API_KEY` in `.env`** — AI agent non-functional without it
- [ ] **Run `main.py status`** — Baseline data freshness numbers
- [x] **Update `.agents/` memory files** — Were 5 months stale *(done 2026-10-02)*

---

## Phase 2 — Remaining Work

### 🔴 P0 — Critical Path

- [x] **Groww field mapping fix** — Full rewrite done *(done 2026-04-29)*
- [x] **Groww TOTP auth flow** — Implemented *(done 2026-04-29)*
- [x] **Portfolio P&L with current prices** — `portfolio_analyzer.py` *(done)*
- [x] **Data freshness / daily price pipeline** — `price_scheduler.py` + APScheduler *(done)*
- [x] **ML pipeline v2** — 14 features, HistGradientBoosting, time-split *(done)*
- [x] **Signal engine** — RAG-style ML → AI → BUY/HOLD/SKIP *(done)*
- [x] **Auth system** — Google OAuth + login/register pages *(done)*
- [x] **Admin dashboard** — Admin routes + frontend page *(done)*
- [ ] **AI agent portfolio deep integration** — Inject full P&L + holdings into agent context
  - Owner: ai-ml
  - Needs: Inject portfolio summary into system prompt, add portfolio-aware tools

### 🟡 P1 — Important

- [ ] **Risk metrics for portfolio** — Beta, sector allocation %, concentration
  - Owner: backend + ai-ml
  - Needs: Portfolio data + price correlation calculations

- [ ] **Mutual fund support (basic)** — Ingest AMFI NAV data
  - Owner: data-engineer
  - Needs: New fetch script, schema update for MF-specific fields

- [ ] **Stock comparison UI** — Side-by-side display
  - Owner: frontend
  - Needs: Backend already has compare_stocks tool — need UI for it

- [ ] **Watchlist feature** — Save stocks, see quick status
  - Owner: backend + frontend
  - Needs: New table `watchlist_items`, API endpoints, frontend UI

- [ ] **Data quality dashboard** — Visual overview of data health
  - Owner: data-engineer + frontend
  - Needs: Quality metric queries, new page/component

### 🟢 P2 — Backlog

- [ ] **Goal-based planning** — Link investment plans to life goals
- [ ] **Historical portfolio value** — Track total value over time
- [ ] **Mobile responsiveness** — Polish small screen experience
- [ ] **Export functionality** — PDF/CSV reports
- [ ] **News sentiment analysis** — FinBERT or similar NLP
- [ ] **Automated alerts** — Price targets, unusual activity triggers
- [ ] **Tax-aware recommendations** — LTCG/STCG impact analysis

---

## Tech Debt

- [ ] Add Pydantic request validation to API endpoints
- [ ] Implement API rate limiting
- [ ] Normalize financial JSON keys across companies
- [ ] Add connection pooling for DataStore
- [ ] Persist agent conversation memory across sessions
- [ ] Add comprehensive error handling to frontend (error.tsx)
- [ ] Add test suite (pytest backend, Playwright frontend)
- [ ] API versioning (`/api/v1/*`)
- [ ] Database migrations framework (for Postgres transition)

---

## Done (Archive)

<details>
<summary>Completed items (click to expand)</summary>

- [x] Nifty 500 stock list ingestion
- [x] 5-year OHLCV price data pipeline
- [x] Quarterly financial statements pipeline
- [x] News pipeline (GNews + RSS)
- [x] Nifty 500 index data
- [x] 8 discovery buckets
- [x] Market pulse (breadth, sentiment)
- [x] Sector performance grid
- [x] AI chat agent (13+ tools, SSE streaming)
- [x] Stock detail page
- [x] FastAPI backend + Next.js frontend
- [x] User profile, investment plans, portfolio CRUD
- [x] Railway + Vercel deployment
- [x] Groww integration rewrite
- [x] Price scheduler (APScheduler)
- [x] ML pipeline v2
- [x] Signal engine (RAG-style)
- [x] Auth system (Google OAuth)
- [x] Admin dashboard
- [x] Backtester
- [x] Audit logger
- [x] Alternative assets support
- [x] Switch to Gemini 2.5 Flash

</details>
