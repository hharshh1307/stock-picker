# 🎯 Stock Picker — Project Objective

## Mission

Build **India's best personal AI-powered investment platform** — a tool that combines comprehensive market data, intelligent analysis, and personalized financial planning to help individual investors make informed, data-driven decisions across the Indian equity market and beyond.

## Vision (Long-Term)

A platform where a user can:
- **Discover** opportunities across stocks, mutual funds, ETFs, and other asset classes
- **Analyze** any investment with deep fundamentals, technicals, and sentiment data
- **Plan** their financial future with goal-based, frequency-aware investment strategies
- **Track** portfolio performance with real-time P&L, risk metrics, and rebalancing suggestions
- **Chat** with an AI financial expert that knows their portfolio, risk profile, and goals
- **Act** on ML-powered signals with confidence (RAG pipeline: ML → AI → BUY/HOLD/SKIP)
- **Learn** from market movements with personalized alerts and educational insights

---

## Current Phase: **Phase 2 — Partially Complete**

### What We Have (Phase 1 ✅ + Phase 2 partial ✅)
- Nifty 500 stock discovery (8 buckets, market pulse, sector grid, movers)
- AI chat agent ("Nifty Sage") — Gemini 2.5 Flash, 13+ tools, SSE streaming
- Data pipeline: prices (5yr OHLCV), quarterly financials, news (GNews + RSS)
- ML pipeline v2: 14 features, HistGradientBoosting, 3 horizons (1d/1w/1m)
- Signal engine: RAG-style ML retrieval → AI analysis → BUY/HOLD/SKIP
- SQLite database (~80MB of stock data)
- FastAPI backend + Next.js 16 frontend (Tailwind + shadcn/ui)
- Google OAuth authentication + admin dashboard
- User profile, investment plans, portfolio tracking
- Groww broker integration (read-only, TOTP-capable)
- Portfolio P&L analyzer with diversification & concentration metrics
- Daily price auto-refresh scheduler (16:00 IST, APScheduler)
- Backtester, audit logger, alternative assets support
- Deployed: Backend on Railway, Frontend on Vercel

### What Still Needs Work (Phase 2 remaining 🔨)
- **AI agent portfolio deep integration** — inject P&L + holdings into agent context
- **Risk metrics dashboard** — beta, sector allocation %, concentration on frontend
- **Data quality dashboard** — visual health of data pipeline
- **Watchlist feature** — save and monitor stocks
- **Stock comparison UI** — side-by-side view (backend already supports it)

### What's Next (Phase 3 🔮)
- Mutual fund support (AMFI NAV data)
- News sentiment analysis (NLP/FinBERT)
- Anomaly detection (unusual price/volume patterns)
- Portfolio optimization (mean-variance, rebalancing)
- Automated alerts & watchlists
- Global market context (US markets, crypto, commodities)
- Tax-aware recommendations (LTCG/STCG impact)
- Goal-based financial planning

### Phase 4 (Future 💎)
- Postgres migration for multi-user scale
- API rate limiting & versioning
- PWA / mobile app
- Community features
- Premium data sources

---

## North Star Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Data freshness | Prices < 1 day old | Auto-scheduler built, freshness unknown |
| Stock coverage | 500+ (Nifty 500) | ~500 stocks (4 NSE indices) |
| AI response quality | Accurate, cited, actionable | Gemini 2.5 Flash — needs GEMINI_API_KEY |
| ML signal quality | Recall@K > 60%, alpha > 0 | Built, metrics in `oot_metrics.json` |
| Portfolio tracking accuracy | 100% P&L accuracy | Basic (no XIRR yet) |
| Frontend performance | < 2s page load | Unknown (needs profiling) |
| Data quality score | > 95% completeness | Unknown (needs dashboard) |
| Test coverage | > 70% | 0% (no test suite) |

---

## Core Principles

1. **Data first** — Every recommendation must be backed by real data, never hallucinated
2. **Personal context** — The AI must know the user's portfolio, risk tolerance, and goals
3. **Indian market focus** — INR formatting, SEBI compliance disclaimers, NSE/BSE context
4. **Cost efficient** — Use free/cheap data sources; Gemini Flash for most queries
5. **Progressive complexity** — Start simple, add sophistication over time
6. **Production quality** — Not a toy; this is a daily-use financial tool
7. **ML with integrity** — Time-based train/test splits, no data leakage, honest metrics
