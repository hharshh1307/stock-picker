# 📈 Platform Performance Tracking

> Track key performance metrics over time.

---

## API Response Times

| Endpoint | Target | Last Measured | Date |
|----------|--------|--------------|------|
| `/api/discovery/market-pulse` | < 500ms | Not measured | — |
| `/api/discovery/buckets` | < 2s | Not measured | — |
| `/api/discovery/sectors` | < 500ms | Not measured | — |
| `/api/stocks/{symbol}` | < 200ms | Not measured | — |
| `/api/chat` (first token) | < 3s | Not measured | — |

## Frontend Page Load

| Page | Target | Last Measured | Date |
|------|--------|--------------|------|
| Discovery (`/`) | < 2s | Not measured | — |
| Chat (`/chat`) | < 1s | Not measured | — |
| Stock Detail | < 1.5s | Not measured | — |

## Pipeline Execution Times

| Pipeline | Target | Last Measured | Date |
|----------|--------|--------------|------|
| `main.py all` | < 60 min | Not measured | — |
| `main.py prices` | < 30 min | Not measured | — |
| `main.py financials` | < 30 min | Not measured | — |
| `main.py news` | < 15 min | Not measured | — |

## Database Size

| Date | DB Size | Stock Count | Price Records | Financial Records |
|------|---------|-------------|--------------|-------------------|
| 2026-04-21 | ~41MB | ~500 | Unknown | Unknown |

> **Action:** Run `uv run python main.py status` to populate these numbers.

## AI Agent Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Avg tools per query | 3-5 | Not measured |
| Avg response time | < 10s | Not measured |
| Cost per query | < $0.05 | ~$0.01-0.05 |
| Accuracy (subjective) | High | Good |
