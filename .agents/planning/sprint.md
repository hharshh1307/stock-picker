# 🏃 Current Sprint

> **Sprint:** Phase 2 Kickoff
> **Period:** 2026-04-21 → TBD
> **Goal:** Make the portfolio actually useful — show P&L, ensure data freshness

---

## Sprint Focus

### 🎯 Sprint Goal
*"A user should be able to see their portfolio's current value and unrealized P&L, know when data was last refreshed, and get portfolio-aware responses from the AI."*

### Tasks This Sprint

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Portfolio P&L calculation backend | backend | [ ] | Add method to compute current value per holding |
| 2 | Portfolio P&L display frontend | frontend | [ ] | Show value, cost, gain/loss, % change |
| 3 | Data freshness query endpoint | data/backend | [ ] | MAX dates for prices, financials, news |
| 4 | Freshness badges on frontend | frontend | [ ] | Show "Updated 2h ago" style indicators |
| 5 | Agent portfolio context enhancement | ai-ml | [ ] | Inject P&L data into system prompt |

### Definition of Done
- [ ] Portfolio page shows current value and P&L per holding
- [ ] Discovery page shows data freshness indicator
- [ ] AI agent references portfolio holdings in relevant responses
- [ ] All changes deployed to Railway + Vercel

---

## Parking Lot (Not This Sprint)
- Mutual fund support
- Watchlist
- Risk metrics
- Stock comparison UI
