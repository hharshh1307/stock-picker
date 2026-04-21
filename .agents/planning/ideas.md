# 💡 Ideas Backlog

> Raw ideas, half-baked concepts, and wild possibilities. No idea is too small or too crazy.
> Filter and promote to roadmap/todos when ready.

---

## Feature Ideas

### 💡 "Morning Brief" — Daily Market Summary
**Category:** AI / UX
**One-liner:** Auto-generated morning email/notification with overnight market changes, portfolio impact, and top opportunities.
**Why:** Users check markets every morning — give them a personalized briefing.

### 💡 "What If" Scenario Analysis
**Category:** AI / Portfolio
**One-liner:** "What if I invest ₹10K in TCS monthly for 5 years?" — show projected outcomes with backtested data.
**Why:** Helps users visualize long-term impact of investment decisions.

### 💡 Sector Rotation Detector
**Category:** Analysis / ML
**One-liner:** Automatically detect when money is flowing from one sector to another (volume + price trends).
**Why:** Sector rotation is one of the strongest market signals.

### 💡 "Risk Buddy" — Portfolio Risk Score
**Category:** Portfolio / ML
**One-liner:** Single 0-100 score showing overall portfolio risk based on concentration, beta, correlation, volatility.
**Why:** Most retail investors don't know how risky their portfolio actually is.

### 💡 Dividend Calendar
**Category:** Data / UX
**One-liner:** Show upcoming dividend dates for portfolio stocks and watchlist.
**Why:** Dividend income is important for many Indian investors.

### 💡 Peer Comparison
**Category:** Analysis
**One-liner:** "How does RELIANCE compare to its industry peers?" — automatic peer group selection.
**Why:** Stock analysis is meaningless without industry context.

### 💡 Corporate Action Tracker
**Category:** Data
**One-liner:** Track splits, bonuses, rights issues, buybacks for portfolio stocks.
**Why:** These events significantly impact stock price and holdings.

### 💡 Tax Harvest Suggestions
**Category:** Portfolio / AI
**One-liner:** At financial year end, suggest which stocks to sell for LTCG/STCG tax optimization.
**Why:** Tax planning directly impacts investment returns for Indian investors.

### 💡 Mutual Fund Overlap Checker
**Category:** Analysis
**One-liner:** Show overlap between mutual fund holdings — "these 3 MFs hold 80% same stocks."
**Why:** Indian investors often over-diversify into similar MFs.

### 💡 IPO Tracker & Analysis
**Category:** Data / AI
**One-liner:** Track upcoming IPOs, analyze GMP, show subscription status, AI-powered IPO analysis.
**Why:** IPOs are hugely popular with Indian retail investors.

---

## Data Source Ideas
- NSE corporate announcements RSS feed
- BSE API for real-time prices (backup to yfinance)
- AMFI daily NAV file for mutual funds
- RBI forex data for USD/INR context
- Moneycontrol forums sentiment
- Reddit r/IndianStockMarket sentiment

## UX Ideas
- Dark/light theme toggle
- Customizable dashboard layout
- Keyboard shortcuts for power users
- Chart annotation tool
- Swipe gestures on mobile

## Technical Ideas
- WebSocket for real-time price updates (market hours)
- Edge caching for discovery data (5 min TTL)
- Pre-computed daily reports (batch job at market close)
- SQLite → DuckDB for analytical queries (faster aggregations)
