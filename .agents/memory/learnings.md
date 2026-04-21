# 🎓 Learnings

> What worked, what didn't, what surprised us.

---

### Data Pipeline
- yfinance batch size of 50 is the sweet spot — larger batches get throttled
- 3-second delay between batches prevents most rate limiting
- nselib can be flaky; sometimes returns empty DataFrames
- RSS feeds (ET, MoneyControl) are more reliable than GNews for market news
- GNews free tier (100/day) only covers ~20% of the Nifty 500 universe

### AI Agent
- Temperature 0.3 gives best balance of accuracy and readability
- Agent tends to over-call tools if not guided in the system prompt
- Tool usage strategy table in the prompt significantly improves tool selection
- Dynamic context injection (portfolio, plans) makes responses more relevant
- tiktoken summarization at 40K tokens keeps conversations manageable

### Frontend
- Server components for data-heavy pages (discovery) significantly reduce client JS
- Recharts sparklines are lightweight and render well
- shadcn/ui provides excellent dark mode support out of the box
- SSE streaming for chat gives good UX but needs careful error handling

### Deployment
- Railway auto-deploys from git push — keep main branch clean
- Vercel preview deployments are useful for frontend testing
- CORS needs explicit origins — can't use wildcard with credentials
