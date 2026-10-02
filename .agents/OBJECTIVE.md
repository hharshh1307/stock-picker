# 🎯 Stock Picker — Project Objective

## Mission

Build **India's best personal AI-powered investment platform** — a semi-automated financial expert that recommends investment decisions based on your portfolio, goals, and risk profile. Powered by a combination of **Data Science**, **Classical ML**, and **AI Engineering**.

This project is also a **personal learning vehicle** across 4 domains.

---

## 🧠 Learning Goals (Why This Project Exists)

This project isn't just a product — it's a structured way to gain deep, hands-on expertise across four interconnected fields by building something real.

### 1. 📈 Core ML (Classical Machine Learning)
**Goal:** Understand what ML models we're using, why, and how they work.

**What we're building:**
- **HistGradientBoosting** (scikit-learn) — not deep learning, not LLMs. Classical tabular ML.
  - *Why this model:* Stock data is tabular (rows = stocks, columns = features). Gradient boosting is the gold standard for tabular data. It outperforms neural nets on structured data.
  - *What it predicts:* "Will this stock outperform the Nifty 500 index over the next 1 day / 1 week / 1 month?"
  - *Two model types:* Regressor (predicts % return) + Classifier (predicts outperform yes/no)
- **14 engineered features:** Price momentum (1d/5d/20d/90d returns), volatility, SMA distances, volume ratios, RSI, MACD, Bollinger Band %B, 52-week high/low distance, relative strength vs index
- **Time-based train/test split:** Train on data before July 2025, test on data after. No data leakage — this is how real quant funds validate.

**What you'll learn:**
- Feature engineering for financial data
- Why gradient boosting > neural nets for tabular data
- Train/test methodology that doesn't lie to you
- How to evaluate ML models honestly (Recall@K, alpha, ROC-AUC)

### 2. 📊 Data Science (Data Processing & Understanding)
**Goal:** Understand how raw market data becomes actionable intelligence.

**What we're building:**
- **Data pipeline:** Raw NSE data → cleaned → stored in SQLite → features engineered → ML predictions
- **5 data sources:** yfinance (prices), nselib (stock lists), GNews (news), RSS feeds, screener.in
- **Discovery engine:** 8 "smart buckets" computed from raw data (momentum leaders, beaten-down stocks, volume surges, revenue rockets, etc.)
- **Market intelligence:** Breadth analysis, sector performance, top movers

**What you'll learn:**
- ETL pipeline design (Extract → Transform → Load)
- Data quality issues in real financial data (missing values, stale tickers, corporate actions)
- How to compute financial metrics from raw OHLCV data
- SQL as the backbone of data analysis

### 3. 🤖 AI Engineering (Agents, Loops, Intelligence)
**Goal:** Build progressively smarter AI systems — from simple chat to self-learning pipelines.

**What we're building (progressive roadmap):**
1. ✅ **ReAct Agent** — Single agent with 13+ tools, tool-calling loop (already built)
2. ✅ **RAG Signal Pipeline** — ML retrieval → AI generation → structured output (already built)
3. 🔨 **Portfolio-aware agent** — Agent that knows your holdings, P&L, goals
4. 🔮 **Intent classification** — Route queries to specialized flows
5. 🔮 **Self-learning loop** — Signal outcomes feed back to improve future recommendations
6. 🔮 **Multi-agent orchestration** — Specialized agents (analyst, risk manager, portfolio optimizer)
7. 🔮 **Memory & context management** — Persistent conversation, user preference learning

**What you'll learn:**
- Agent design patterns (ReAct, tool-calling, RAG)
- Prompt engineering for financial analysis
- Streaming responses (SSE)
- Building feedback loops (signal → decision → outcome → learning)
- Evaluation of AI system quality

### 4. 💰 Finance Learning (Domain Knowledge)
**Goal:** Build foundational understanding of financial instruments and investment strategy.

**What you'll learn through building:**
- **Stocks:** What moves prices, how to read financial statements, what P/E, P/B, ROE mean
- **Mutual Funds:** NAV, expense ratios, direct vs regular, SIP vs lump sum
- **Options:** Calls/puts, strike price, expiry, basic strategies (covered calls, protective puts)
- **Other instruments:** ETFs, bonds, gold, REITs, fixed deposits
- **Investment timing:** SIP (systematic investment plan), market timing myths, dollar-cost averaging
- **Risk management:** Diversification, portfolio allocation, correlation, drawdown
- **Indian market specifics:** SEBI regulations, LTCG/STCG tax, NSE/BSE mechanics, settlement cycles

---

## 🎯 End Goal

A **semi-automated financial expert** that:
1. **Ingests** real-time market data automatically (prices, news, financials)
2. **Analyzes** using ML models + AI reasoning — not just one or the other
3. **Recommends** specific BUY/HOLD/SELL decisions with clear rationale
4. **Personalizes** to YOUR portfolio, risk tolerance, and financial goals
5. **Learns** from outcomes — was the recommendation right? Feed that back.
6. **Teaches** you — explains the "why" behind every recommendation in plain language

The human remains in the loop for final decisions. The system does the heavy lifting of research, analysis, and monitoring.

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

### Phase 3: Intelligence & Multi-Asset 🔮
- Mutual fund support (AMFI NAV data)
- Self-learning signal loop (outcomes → model retraining)
- News sentiment analysis (FinBERT)
- Portfolio optimization (mean-variance)
- Automated alerts
- Tax-aware recommendations

### Phase 4: Scale & Polish 💎
- Postgres migration, API hardening, test suite
- PWA / mobile, community features
- Premium data sources

---

## North Star Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Data freshness | Prices < 1 day old | Auto-scheduler built |
| Stock coverage | 500+ (Nifty 500) | ~500 stocks |
| ML signal quality | Recall@K > 60%, alpha > 0 | Built, needs validation |
| AI recommendation quality | Accurate, cited, actionable | Gemini 2.5 Flash |
| Portfolio tracking accuracy | 100% P&L, XIRR | Basic (no XIRR yet) |
| Learning progress | Document learnings per session | Starting now |

---

## Core Principles

1. **Data first** — Every recommendation backed by real data, never hallucinated
2. **Learn by building** — Every feature is a learning opportunity in ML/DS/AI/Finance
3. **Human in the loop** — Semi-automated, not fully automated. YOU decide.
4. **Indian market focus** — INR formatting, SEBI compliance, NSE/BSE context
5. **Honest ML** — Time-based splits, no data leakage, report real metrics
6. **Progressive complexity** — Start simple, add sophistication as understanding grows
7. **Production quality** — Not a toy; this is a daily-use financial tool
