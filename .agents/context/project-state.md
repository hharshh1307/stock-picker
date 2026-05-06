# 📊 Project State Snapshot

> **Last Updated:** 2026-04-29
> **Updated By:** Antigravity (AI Assistant)

## Current Status: 🟡 Active Development — Groww Integration Fixed, Phase 2 In Progress

---

### What's Running

| Service | Status | Notes |
|---|---|---|
| Backend (FastAPI) | ✅ Running | localhost:8000 / Railway deployed |
| Frontend (Next.js) | ✅ Running | localhost:3001 / Vercel deployed |
| Database (SQLite) | ✅ Active | `stock_picker.db` (~41MB) |
| AI Agent (GPT-4o) | ✅ Working | 14+ tools, SSE streaming, ReAct loop |
| Groww Live Sync | 🔴 Was Broken → ✅ Fixed | See below |

---

### What Was Fixed (2026-04-29)

**Groww Integration (`groww_integration.py`) — Complete rewrite:**
- 🔴 **Fixed**: Wrong field names — was reading `avgPrice`, `companyName`, `scripType` (don't exist in API). Now correctly reads `average_price`, `trading_symbol`.
- 🔴 **Fixed**: Wrong response key — was reading `.get('data', [])`, API actually returns `{ "holdings": [...] }`.
- 🟠 **Added**: `get_available_margin_details()` — now fetches real buying power (CNC balance available).
- 🟠 **Added**: `get_user_profile()` — fetches UCC, active_segments, DDPI status.
- 🟠 **Added**: Per-segment position fetching (`SEGMENT_CASH`, `SEGMENT_FNO` if active).
- 🟡 **Added**: TOTP auth flow as 1st preference (no daily re-approval needed). Add `GROWW_TOTP_SECRET` to `.env` to activate.
- 🟡 **Added**: `timeout=10` on all API calls (prevents hangs).
- 🟢 **Added**: `fetch_position_for_symbol(symbol)` — new on-demand per-stock position lookup.

**Agent Tools (`agent_tools.py`) — Updated:**
- `get_portfolio_analysis` now returns `available_cash_inr`, `account_info`, `intraday_positions`.
- New tool: `get_groww_position_for_symbol(symbol)` — registered in TOOL_SCHEMAS and dispatcher.

---

### Data Freshness

| Data Type | Last Refreshed | Record Count | Notes |
|---|---|---|---|
| Stock list | Unknown | ~500 | Nifty 500 via nselib |
| Prices | Unknown | Run `main.py status` | 2yr daily OHLCV |
| Financials | Unknown | Run `main.py status` | Quarterly |
| News | Unknown | Run `main.py status` | GNews + RSS |
| Index data | Unknown | Run `main.py status` | Nifty 500 index |

> ⚠️ Run `uv run python main.py status` to populate actual numbers.

---

### Known Issues

- [ ] XIRR / time-weighted returns not implemented in portfolio P&L
- [ ] Dividend income not tracked
- [ ] No automated pipeline scheduling (manual `main.py all`)
- [ ] `GROWW_TOTP_SECRET` not yet in `.env` (TOTP flow dormant until added)
- [ ] Order placement APIs not implemented (read-only integration)
- [ ] SQLite may bottleneck at scale (Postgres migration in roadmap)

---

### Environment

- Python 3.12+, Node.js 18+
- `.env` requires:
  ```
  OPENAI_API_KEY=...
  GROWW_TOKEN=...          # Groww API key
  GROWW_API_SECRET=...     # Groww API secret (Key+Secret flow)
  GROWW_TOTP_SECRET=...    # Optional: TOTP base32 secret (no-expiry flow)
  ```
- Frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

### Recent Changes

- (2026-04-29) `groww_integration.py` — full rewrite fixing field mapping bugs, adding TOTP, margin, user profile, per-segment positions, per-symbol position lookup
- (2026-04-29) `agent_tools.py` — wired new Groww fields into `get_portfolio_analysis`, added `get_groww_position_for_symbol` tool
- (2026-04-27) Alternative assets support (`alternative_assets.py`)
- (2026-04-22) ML pipeline, backtester, audit logger added
- (2026-04-21) Phase 1 complete: AI agent, 13 tools, portfolio CRUD, frontend chat

---

### Blockers

- Groww TOTP secret not yet configured — daily re-approval needed for live sync until added
