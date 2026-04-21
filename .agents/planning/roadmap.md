# 🗺️ Roadmap

> Phased feature roadmap aligned with OBJECTIVE.md

---

## Phase 1: Foundation ✅ COMPLETE
*Nifty 500 stock discovery platform with AI chat*

- [x] Nifty 500 stock list ingestion (nselib + yfinance)
- [x] 2-year OHLCV price data pipeline
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

## Phase 2: Smart Portfolio & Data Quality 🔨 IN PROGRESS
*Make the tool actually useful for daily portfolio management*

### P0 — Must Have
- [ ] **Portfolio P&L dashboard** — Current value, total gain/loss, daily change per holding
- [ ] **Data freshness tracking** — Show last refresh date, flag stale data
- [ ] **Automated pipeline scheduling** — Daily price refresh at minimum
- [ ] **AI agent portfolio integration** — Deep portfolio-aware analysis in chat

### P1 — Should Have
- [ ] **Risk metrics** — Portfolio beta, sector allocation %, concentration risk
- [ ] **Mutual fund basic support** — AMFI NAV data, display alongside stocks
- [ ] **Stock comparison page** — Side-by-side UI for 2-5 stocks
- [ ] **Watchlist feature** — Save and monitor stocks of interest
- [ ] **Data quality dashboard** — Completeness, coverage, pipeline success rates

### P2 — Nice to Have
- [ ] **Goal-based planning** — Map plans to goals (retirement, house, education)
- [ ] **Historical P&L** — Track portfolio value over time
- [ ] **Mobile responsiveness** — Polish for phone/tablet use
- [ ] **Export reports** — PDF/CSV export of portfolio analysis

---

## Phase 3: Intelligence Layer 🔮 PLANNED
*ML-powered insights and advanced analysis*

- [ ] **Stock scoring model** — Composite score (fundamentals + technicals + sentiment)
- [ ] **News sentiment analysis** — FinBERT or similar NLP on news
- [ ] **Anomaly detection** — Flag unusual price/volume patterns
- [ ] **Portfolio optimization** — Mean-variance, rebalancing suggestions
- [ ] **Automated alerts** — Price targets, unusual activity, portfolio triggers
- [ ] **Global market context** — US markets, crude, USD/INR impact analysis
- [ ] **Tax-aware recommendations** — LTCG/STCG impact on buy/sell decisions

---

## Phase 4: Scale & Polish 💎 FUTURE
*Production hardening and growth features*

- [ ] **Postgres migration** — Move from SQLite for multi-user support
- [ ] **User authentication** — Multi-user with separate portfolios
- [ ] **API rate limiting** — Protect backend from abuse
- [ ] **PWA / mobile app** — Installable app experience
- [ ] **Community features** — Share analyses, follow strategies
- [ ] **Premium data sources** — Consider paid APIs for better reliability
