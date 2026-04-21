# 📊 Data Quality Tracker

> Monitor data freshness, completeness, and accuracy.

---

## Data Freshness

| Data Type | Last Refresh | Freshness Target | Status |
|-----------|-------------|-----------------|--------|
| Stock list | Unknown | Weekly | ⚠️ Check |
| Price data | Unknown | Daily (trading days) | ⚠️ Check |
| Financials | Unknown | Quarterly | ⚠️ Check |
| News | Unknown | Daily | ⚠️ Check |
| Index data | Unknown | Daily | ⚠️ Check |

> **To check:** Run `uv run python main.py status` and update this table.

## Data Completeness

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Stocks in DB | 500 | ~500 | Nifty 500 universe |
| Stocks with prices | 495+ | Unknown | Some may fail yfinance |
| Stocks with financials | 450+ | Unknown | Not all have data |
| Stocks with news | 100+ | Unknown | GNews limits coverage |
| Stocks with sector info | 500 | ~500 | From yfinance enrichment |

## Known Quality Issues

1. **Financial JSON key inconsistency** — Different companies use different field names (e.g., "Total Revenue" vs "Operating Revenue"). Affects revenue/profit calculations in discovery buckets.

2. **Zero volume data** — Some thinly traded small-cap stocks show 0 volume on certain days. Affects volume spike calculations.

3. **Yahoo symbol mapping edge cases** — A few stocks may have incorrect `.NS` suffix mapping, causing price fetch failures.

4. **News recency** — GNews free tier limits to 100 searches/day. Many stocks have no recent news in the database.

5. **Missing quarters** — Some companies may have gaps in quarterly financial data (failed fetches or corporate events).

## Quality Check SQL Queries

```sql
-- Freshness check
SELECT 'prices' as type, MAX(date) as latest FROM prices
UNION ALL
SELECT 'financials', MAX(period_ending) FROM quarterly_financials
UNION ALL
SELECT 'news', MAX(published_at) FROM news;

-- Stocks missing recent prices
SELECT COUNT(*) FROM stocks s
WHERE NOT EXISTS (
  SELECT 1 FROM prices p 
  WHERE p.symbol = s.symbol AND p.date >= date('now', '-7 days')
);

-- Financial coverage
SELECT COUNT(DISTINCT symbol) as covered,
       (SELECT COUNT(*) FROM stocks) as total
FROM quarterly_financials;
```

## Quality Improvement Actions

- [ ] Run full pipeline and update freshness numbers
- [ ] Identify stocks with missing/stale data
- [ ] Normalize financial JSON keys (create mapping table)
- [ ] Add data validation to pipeline (reject bad records)
- [ ] Set up daily automated freshness check
