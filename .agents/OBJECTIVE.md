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
- **Learn** from market movements with personalized alerts and educational insights

---

## Current Phase: **Phase 1 — Foundation Complete, Transitioning to Phase 2**

### What We Have (Phase 1 ✅)
- Nifty 500 stock discovery (8 buckets, market pulse, sector grid, movers)
- AI chat agent ("Nifty Sage") with 13 tools, streaming responses
- Data pipeline: prices (2yr OHLCV), quarterly financials, news (GNews + RSS)
- SQLite database with ~41MB of stock data
- FastAPI backend + Next.js 16 frontend (Tailwind + shadcn/ui)
- User profile, investment plans, portfolio tracking (basic CRUD)
- Deployed: Backend on Railway, Frontend on Vercel

### What We're Building (Phase 2 🔨)
- **Multi-asset support**: Mutual funds, ETFs, indices alongside stocks
- **Smart portfolio analytics**: P&L tracking, XIRR, sector allocation, risk metrics
- **Enhanced AI agent**: Portfolio-aware advice, risk assessment, rebalancing suggestions
- **Better data quality**: More reliable sources, freshness tracking, gap detection
- **Goal-based planning**: Map investment plans to financial goals

### What's Next (Phase 3 🔮)
- ML-powered stock screening & scoring models
- Sentiment analysis on news (NLP)
- Automated alerts & watchlists
- Global market awareness (US markets, crypto, commodities for context)
- Mobile-responsive PWA or native app
- Social features: share analysis, community picks

---

## North Star Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Data freshness | Prices < 1 day old | ~varies (manual pipeline) |
| Stock coverage | 500+ (Nifty 500) | ~500 stocks |
| AI response quality | Accurate, cited, actionable | Good but improvable |
| Portfolio tracking accuracy | 100% P&L accuracy | Basic (no XIRR yet) |
| Frontend performance | < 2s page load | ~OK (needs profiling) |
| Data quality score | > 95% completeness | Unknown (needs tracking) |

---

## Core Principles

1. **Data first** — Every recommendation must be backed by real data, never hallucinated
2. **Personal context** — The AI must know the user's portfolio, risk tolerance, and goals
3. **Indian market focus** — INR formatting, SEBI compliance disclaimers, NSE/BSE context
4. **Cost efficient** — Use free/cheap data sources; GPT-4o only when needed, mini for simple queries
5. **Progressive complexity** — Start simple, add sophistication over time
6. **Production quality** — Not a toy; this is a daily-use financial tool
