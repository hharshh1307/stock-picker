# 📊 Project State Snapshot

> **Last Updated:** 2026-04-21
> **Updated By:** Initial setup

## Current Status: 🟢 Functional — Discovery + Chat + Portfolio CRUD working

### What's Running
- **Backend**: FastAPI on localhost:8000 (Railway deployed)
- **Frontend**: Next.js on localhost:3001 (Vercel deployed)
- **Database**: SQLite at `data/stock_picker.db` (~41MB)
- **AI Agent**: GPT-4o with 13 tools, SSE streaming

### Data Freshness
| Data Type | Last Refreshed | Record Count | Notes |
|-----------|---------------|--------------|-------|
| Stock list | Unknown | ~500 | Nifty 500 via nselib |
| Prices | Unknown | Check via `main.py status` | 2yr daily OHLCV |
| Financials | Unknown | Check via `main.py status` | Quarterly (income, balance, cashflow) |
| News | Unknown | Check via `main.py status` | GNews + RSS |
| Index data | Unknown | Check via `main.py status` | Nifty 500 index |

> ⚠️ **Action needed**: Run `uv run python main.py status` to populate these numbers.

### Known Issues
- [ ] Data freshness not automatically tracked
- [ ] No automated pipeline scheduling (manual `main.py all` runs)
- [ ] Portfolio P&L calculation is basic (no XIRR, no dividends)
- [ ] AI agent doesn't deeply integrate portfolio context yet
- [ ] No data quality scoring or gap detection
- [ ] SQLite may become a bottleneck at scale

### Environment
- Python 3.12+, Node.js 18+
- `.env` requires: `OPENAI_API_KEY`
- Frontend `.env.local` needs: `NEXT_PUBLIC_API_URL=http://localhost:8000`

### Recent Changes
- (2026-04-20) Added user profile, investment plans, portfolio CRUD
- (2026-04-20) Expanded models for multi-asset support (AssetType enum)
- (2026-04-20) Settings page on frontend

### Blockers
- None currently — ready for Phase 2 development
