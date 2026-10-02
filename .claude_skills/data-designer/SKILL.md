---
name: data-designer
description: Generate synthetic financial data and build data pipelines for stock market analysis, including synthetic price series, fundamental data, and technical indicators
argument-hint: [data-type] [parameters]
context: fork
agent: general-purpose
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Data Designer — Synthetic Financial Data Generator

Generating: **$ARGUMENTS**

## Overview
Create synthetic financial market data for testing, prototyping, and ML pipeline development when real data is unavailable or insufficient.

## Common Data Types

### 1. Synthetic Price Series
```markdown
### Synthetic OHLCV Data for [SYMBOL]
- **Period:** 2 years daily data
- **Price range:** ₹[MIN] - ₹[MAX]
- **Trend:** [UP/DOWN/SIDEWAYS] with [volatility]% daily volatility
- **Volume pattern:** [Normal/High/Low] volume typical for [SECTOR]
- **Technical indicators:** SMA 20/50, RSI 14, volatility computed
```

### 2. Synthetic Fundamental Data
```markdown
### Synthetic Quarterly Financials for [SYMBOL]
- **Revenue:** ₹[VALUE] Crores (QoQ growth: [PERCENT]%)
- **Net Income:** ₹[VALUE] Crores (Margin: [PERCENT]%)
- **EBITDA:** ₹[VALUE] Crores
- **Total Equity:** ₹[VALUE] Crores
- **Total Debt:** ₹[VALUE] Crores
- **Promoter Holding:** [PERCENT]%
- **FII/DII Interest:** [PERCENT]% / [PERCENT]%
```

### 3. Technical Indicator Data
```markdown
### Technical Indicators for [SYMBOL] (90-day history)
- **SMA 20:** ₹[VALUE]
- **SMA 50:** ₹[VALUE]
- **RSI 14:** [VALUE] ([OVERBOUGHT/OVERSOLD/NEUTRAL])
- **Volatility 20d:** [PERCENT]%
- **52-week high:** ₹[VALUE] on [DATE]
- **52-week low:** ₹[VALUE] on [DATE]
```

## Pipeline Patterns

### Price Data Generation Workflow
```
1. Define symbol and sector
2. Set trend direction and volatility parameters
3. Generate OHLCV series with realistic autocorrelation
4. Compute technical indicators (SMA, RSI, volatility)
5. Add sector-specific patterns (momentum mean-reversion, etc.)
6. Output as JSON compatible with storage schema
```

### Fundamental Data Generation
```
1. Set revenue growth trajectory (linear/exponential/declining)
2. Set profit margin baseline with sector typicals
3. Compute EBITDA from revenue and margins
4. Set capital structure (debt/equity ratio)
5. Add quarterly variation (seasonality, one-time items)
6. Output with consistent JSON schema
```

## Quality Checklist
- [ ] Price series has realistic autocorrelation and volatility clustering
- [ ] Technical indicators are mathematically consistent with price data
- [ ] Fundamental data balances (revenue → EBITDA → net income flow)
- [ ] Sector-specific patterns are preserved (some sectors mean-revert, others trend)
- [ ] 52-week high/low are within generated range
- [ ] Volume data matches price movement intensity
- [ ] Data schema matches `data_store.py` expectations

## Integration with Stock Picker Agent
This skill integrates with the Financial Expert Agent by providing:
- Synthetic data for tool testing without requiring live API calls
- Prototype fundamental data for new stock analysis workflows
- ML pipeline training data when historical data is insufficient
- Edge case scenarios for risk testing (flash crashes, momentum spikes)