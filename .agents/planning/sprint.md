# 🏃 Current Sprint

> **Sprint:** Post-Hiatus Recovery
> **Period:** 2026-10-02 → TBD
> **Goal:** Stabilize project after 5-month gap — commit pending work, verify everything runs, decide next focus

---

## Sprint Focus

### 🎯 Sprint Goal
*"Get the project back to a known-good, committed state. Verify all systems work. Pick the next major feature to build."*

### Tasks This Sprint

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Update `.agents/` memory files | ✅ Done | All files updated to reflect actual state |
| 2 | Commit 705 lines of pending changes | [ ] | Review diff, write meaningful commit message |
| 3 | Set `GEMINI_API_KEY` in `.env` | [ ] | Get key from https://aistudio.google.com/apikey |
| 4 | Run `main.py status` to check data freshness | [ ] | Determine if pipeline needs a full refresh |
| 5 | Test backend startup (`main.py serve`) | [ ] | Verify no import/runtime errors |
| 6 | Test frontend build (`npm run dev` in `web/`) | [ ] | Check for TS errors |
| 7 | Decide next focus area | [ ] | See options below |

### Definition of Done
- [ ] All pending changes committed with clean git status
- [ ] Backend starts without errors
- [ ] Frontend builds without errors
- [ ] Data freshness is known and documented
- [ ] Next work area is chosen

---

## Next Focus Options (Pick One)

| Option | Impact | Effort | Notes |
|--------|--------|--------|-------|
| **A: AI agent portfolio integration** | High | Medium | Make chat portfolio-aware — biggest user value |
| **B: Risk metrics dashboard** | Medium | Medium | Beta, concentration, sector allocation on frontend |
| **C: Watchlist feature** | Medium | Small | New table + API + UI — quick win |
| **D: Stock comparison UI** | Medium | Small | Backend already done — just need frontend |
| **E: Data pipeline refresh** | High | Small | Run full pipeline, ensure data is current |
| **F: Mutual fund support** | High | Large | New data source, schema changes, new pages |

---

## Parking Lot (Not This Sprint)
- News sentiment analysis
- Automated alerts
- Tax-aware recommendations
- Postgres migration
- Test suite
