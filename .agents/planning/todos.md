# ✅ Active TODOs

> All active tasks across agents. Update status as work progresses.
> Mark with: `[ ]` not started, `[~]` in progress, `[x]` done

---

## Phase 2 — Current Sprint

### 🔴 P0 — Critical Path

- [ ] **Portfolio P&L calculation** — Show current value, unrealized gain/loss for each holding
  - Owner: backend + frontend
  - Needs: Latest price lookup for portfolio symbols, P&L math
  - Files: `data_store.py` (new method), `api_routes/user.py`, frontend portfolio page

- [ ] **Data freshness indicators** — Show when data was last refreshed
  - Owner: data-engineer + frontend
  - Needs: Query MAX(date) from prices, MAX(fetched_at) from financials/news
  - Files: `data_store.py`, new API endpoint, frontend badges

- [ ] **Automated pipeline scheduling** — Run price refresh automatically
  - Owner: data-engineer + backend
  - Options: APScheduler, cron job, or Railway scheduled tasks
  - Priority: At minimum, daily price refresh

- [ ] **AI agent portfolio deep integration** — Agent should analyze user's holdings
  - Owner: ai-ml
  - Needs: Inject full portfolio with current P&L into agent context
  - Files: `agent_prompts.py`, `agent_tools.py` (add portfolio tools)

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

---

## Tech Debt

- [ ] Add Pydantic request validation to API endpoints
- [ ] Implement API rate limiting
- [ ] Normalize financial JSON keys across companies
- [ ] Add connection pooling for DataStore
- [ ] Persist agent conversation memory across sessions
- [ ] Add comprehensive error handling to frontend pages

---

## Housekeeping

- [ ] Run `main.py status` to baseline data freshness numbers
- [ ] Update `.agents/context/project-state.md` with current data counts
- [ ] Verify Railway + Vercel deployments are current
