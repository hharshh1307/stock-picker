# 🗺️ Roadmap

> Phased feature roadmap aligned with OBJECTIVE.md

---

## Phase 1: Foundation ✅ COMPLETE
*Nifty 500 stock discovery platform with AI chat*

- [x] Nifty 500 stock list ingestion (nselib + yfinance)
- [x] 5-year OHLCV price data pipeline
- [x] Quarterly financial statements pipeline
- [x] News pipeline (GNews + RSS)
- [x] Nifty 500 index data
- [x] 8 discovery buckets (momentum, beaten down, volume, revenue, profit, 52w high/low, sector outperformers)
- [x] Market pulse (breadth, sentiment, index change)
- [x] Sector performance grid
- [x] AI chat agent (13 tools, SSE streaming)
- [x] Stock detail page
- [x] FastAPI backend + Next.js frontend
- [x] User profile, investment plans, portfolio CRUD
- [x] Railway + Vercel deployment

---

## Phase 2: Smart Portfolio & Data Quality 🟡 PARTIALLY COMPLETE
*Make the tool actually useful for daily portfolio management*

### Done ✅
- [x] **Groww broker integration** — Full rewrite with TOTP, margin, positions
- [x] **Daily price auto-refresh** — APScheduler at 16:00 IST + startup check
- [x] **ML pipeline v2** — 14 features, HistGradientBoosting, 3 horizons
- [x] **Signal engine** — RAG-style ML → AI analysis → BUY/HOLD/SKIP
- [x] **Auth system** — Google OAuth + login/register
- [x] **Admin dashboard** — Admin API + frontend page
- [x] **Portfolio P&L analyzer** — Diversification, concentration, sector allocation
- [x] **Backtester** — Signal performance validation
- [x] **Audit logger** — Chat audit trail
- [x] **Switch to Gemini 2.5 Flash** — Cost-effective, fast

### Remaining 🔨
- [ ] **AI agent portfolio deep integration** — Inject holdings + P&L into agent context
- [ ] **Risk metrics on frontend** — Display beta, concentration, sector allocation
- [ ] **Data quality dashboard** — Visual pipeline health
- [ ] **Watchlist feature** — Save and monitor stocks
- [ ] **Stock comparison UI** — Side-by-side view (backend ready)

---

## Phase 3: Multi-Asset & Intelligence 🔮 PLANNED
*Expand beyond stocks, add smarter analysis*

- [ ] **Mutual fund support** — AMFI NAV data, display alongside stocks
- [ ] **News sentiment analysis** — FinBERT or similar NLP
- [ ] **Anomaly detection** — Flag unusual price/volume patterns
- [ ] **Portfolio optimization** — Mean-variance, rebalancing suggestions
- [ ] **Automated alerts** — Price targets, unusual activity, portfolio triggers
- [ ] **Global market context** — US markets, crude, USD/INR impact
- [ ] **Tax-aware recommendations** — LTCG/STCG impact on buy/sell
- [ ] **Goal-based planning** — Link investment plans to life goals

---

## Phase 4: Scale & Polish 💎 FUTURE
*Production hardening and growth features*

- [ ] **Postgres migration** — Move from SQLite for multi-user support
- [ ] **API rate limiting & versioning** — Production-grade API
- [ ] **Test suite** — pytest + Playwright
- [ ] **PWA / mobile app** — Installable app experience
- [ ] **Community features** — Share analyses, follow strategies
- [ ] **Premium data sources** — Paid APIs for better reliability
- [ ] **Historical portfolio value** — Track total value over time
- [ ] **Export reports** — PDF/CSV of portfolio analysis
