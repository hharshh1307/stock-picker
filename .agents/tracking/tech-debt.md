# 🔧 Technical Debt Register

> Known shortcuts, hacks, and things we need to fix eventually.

---

## High Priority

### No API input validation
- **What:** API endpoints accept any JSON without validation
- **Risk:** Bad data in DB, crashes, potential injection
- **Fix:** Add Pydantic request models to all POST/PUT endpoints
- **Effort:** Medium (1-2 hours)

### No pipeline automation
- **What:** Data refresh requires manual `main.py all` runs
- **Risk:** Stale data, user sees outdated prices
- **Fix:** APScheduler or Railway cron jobs
- **Effort:** Small (30 min)

### Agent memory not persisted
- **What:** Chat conversation resets on page refresh
- **Risk:** User loses context, repeats questions
- **Fix:** Store conversation in DB or Redis, load on reconnect
- **Effort:** Medium

## Medium Priority

### Financial JSON key normalization
- **What:** yfinance returns different key names per company
- **Risk:** Revenue/profit calculations may miss data for some stocks
- **Fix:** Create normalization mapping, apply during ingestion
- **Effort:** Medium

### No connection pooling
- **What:** DataStore creates new sqlite3 connection each time
- **Risk:** Connection overhead, potential issues under load
- **Fix:** Use connection pool or singleton pattern (already partially done)
- **Effort:** Small

### No error boundaries on frontend
- **What:** Some pages crash entirely on API failure
- **Risk:** White screen of death for users
- **Fix:** Add Next.js error.tsx to all route segments
- **Effort:** Small

### Hardcoded CORS origins
- **What:** CORS origins list is hardcoded in api_server.py
- **Risk:** Need code change for every new deployment URL
- **Fix:** Load from environment variable
- **Effort:** Small

## Low Priority

### No database migrations framework
- **What:** Schema changes done via manual ALTER TABLE in `_migrate_schema()`
- **Risk:** Easy to miss migrations, hard to rollback
- **Fix:** Use Alembic or similar (overkill for SQLite, important for Postgres)
- **Effort:** Large

### No API versioning
- **What:** All endpoints at `/api/*` with no version prefix
- **Risk:** Breaking changes affect all clients
- **Fix:** Add `/api/v1/*` prefix when we have external consumers
- **Effort:** Small

### No test suite
- **What:** Zero automated tests
- **Risk:** Regressions go unnoticed
- **Fix:** Add pytest for backend, Playwright for frontend (later)
- **Effort:** Large (ongoing)
