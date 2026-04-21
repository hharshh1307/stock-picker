# 📝 Decision Log

> Every significant decision with rationale. Future you will thank present you.

## Format
```
### [Date] Decision: [Title]
**Context:** Why this came up
**Options:** What we considered
**Decision:** What we chose
**Rationale:** Why
**Impact:** What changes
```

---

### 2026-04-20 Decision: SQLite over Postgres for MVP
**Context:** Needed a database for stock data storage
**Options:** SQLite, Postgres (Supabase), DuckDB
**Decision:** SQLite with WAL mode
**Rationale:** Zero infrastructure, fast prototyping, 41MB is tiny. Migrate to Postgres when we need concurrent writes or scale.
**Impact:** Single-file DB, no connection pooling needed, easy backup

### 2026-04-20 Decision: Single ReAct agent over multi-agent
**Context:** Building AI chat for stock analysis
**Options:** Multi-agent (CrewAI/LangGraph), single ReAct agent
**Decision:** Single GPT-4o agent with 13 tools
**Rationale:** One analyst persona is sufficient for Q&A. Multi-agent adds orchestration overhead with no quality benefit for this use case.
**Impact:** Simpler codebase, easier to debug, lower latency

### 2026-04-20 Decision: yfinance as primary data source
**Context:** Need OHLCV + financials for 500 stocks
**Options:** yfinance (free), NSE API (free but complex), paid APIs
**Decision:** yfinance with retry logic
**Rationale:** Free, covers our needs, Python library. Accept instability and build retry logic around it.
**Impact:** Occasional pipeline failures, need to consider fallback sources

### 2026-04-21 Decision: .agents folder for project intelligence
**Context:** Need structured context, agent personas, and tracking for long-term development
**Options:** Keep using ad-hoc notes, use .claude_agents only, create dedicated .agents system
**Decision:** Create `.agents/` with full context, agent personas, memory, planning, and tracking
**Rationale:** Long-term project needs persistent memory, clear objectives, and specialized agent expertise
**Impact:** All AI assistants get consistent project context
