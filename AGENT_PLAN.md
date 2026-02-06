# Financial Expert Agent - Implementation Plan

## Architecture

Single ReAct-style agent using **OpenAI GPT-4o** with tool calling (function calling). Not a multi-agent system — one analyst persona is sufficient for Q&A.

Uses the raw OpenAI Python SDK (not the Agents SDK or LangChain/LangGraph). The tool-calling loop pattern follows the existing `agents/1_foundations/app.py` codebase.

### Why This Architecture
- User queries require dynamic reasoning: "Should I invest in RELIANCE?" needs the agent to decide which tools to call (price, financials, news, sector data), fetch them, then synthesize
- GPT-4o has the most reliable function calling for chaining 3-7 tool calls per query
- Single agent avoids the orchestration overhead of CrewAI/LangGraph with no quality tradeoff

## LLM Selection

**Primary: GPT-4o** (temperature 0.3 for factual accuracy)
- Cost: ~$0.01-0.05 per query for a personal tool
- The architecture supports swapping to Claude via a `--model` flag

## File Structure (4 new files)

```
stock-picker/
    agent_tools.py          # 13 tool definitions + implementations (~500 lines)
    agent.py                # FinancialExpertAgent class + ReAct loop (~200 lines)
    agent_prompts.py        # System prompt template + dynamic builder (~80 lines)
    chat.py                 # CLI REPL interface (~80 lines)
```

## 13 Tools

| Tool | Purpose | Data Source |
|------|---------|-------------|
| `search_stocks` | Resolve "Reliance" / "IT stocks" to symbols | stocks table (SQL LIKE) |
| `get_stock_info` | Profile + latest price + 52w range + YTD return | stocks + prices tables |
| `get_price_history` | OHLCV + SMA/RSI/volatility stats | prices table |
| `get_financials` | Quarterly income/balance/cashflow (normalized keys) | quarterly_financials table |
| `get_sector_performance` | Sector rankings by avg return | market_intelligence.py |
| `get_top_movers` | Top gainers/losers | market_intelligence.py |
| `get_market_breadth` | Advancing vs declining stocks | market_intelligence.py |
| `get_volume_spikes` | Unusual trading activity | market_intelligence.py |
| `get_financial_highlights` | Market-wide standout financials | market_intelligence.py |
| `get_news` | Stock-specific + market news | news table |
| `compare_stocks` | Side-by-side comparison of 2-5 stocks | prices + financials |
| `calculate_valuation_metrics` | P/E, P/B, D/E, ROE, FCF yield | prices + all financials |
| `web_search` | Real-time news/global trends | DuckDuckGo (free, no API key) |

## System Prompt (Key Elements)

- Persona: "Nifty Sage" — expert Indian equity market analyst
- Analytical framework: Price action -> Fundamentals -> Valuation -> Sector context -> News -> Risk
- Rules: ALWAYS use tools before making claims, cite specific numbers, INR Crores/Lakhs formatting
- Balanced analysis: bull AND bear case for every stock
- Mandatory disclaimer at end of investment recommendations
- Dynamic context: current date, latest price date, total stocks/sectors injected at startup

## Agent Loop

```python
while True:
    response = client.chat.completions.create(model, messages, tools)
    if finish_reason == "tool_calls":
        execute tools -> append results -> loop
    else:
        return final text response
```

Conversation memory: in-memory list with tiktoken-based summarization after ~40K tokens.

## Dependencies (additions to pyproject.toml)

```
openai>=1.68.0
python-dotenv>=1.0.1
tiktoken>=0.8.0
duckduckgo-search>=7.0.0
```

## Sample Queries It Should Handle

| Query | Tools Called |
|-------|------------|
| "Should I invest in RELIANCE?" | get_stock_info, get_price_history, get_financials, get_sector_performance, get_news |
| "Which IT stocks are undervalued?" | search_stocks("Technology"), calculate_valuation_metrics (x multiple), compare_stocks |
| "What's happening in the banking sector?" | get_sector_performance, search_stocks("Financial Services"), get_news |
| "Compare TCS vs INFY" | compare_stocks(["TCS","INFY"]) |
| "Where should I invest 5 lakhs?" | get_market_breadth, get_sector_performance, get_top_movers |
| "Why is Adani falling?" | search_stocks("Adani"), get_price_history, get_news, web_search |

## Implementation Order

1. `agent_tools.py` — all 13 tools with OpenAI function schemas
2. `agent_prompts.py` — system prompt template
3. `agent.py` — agent class with tool-calling loop
4. `chat.py` — CLI interface
5. Update `main.py` — add `chat` subcommand
6. Update `pyproject.toml` — add dependencies
7. Create `.env` — OPENAI_API_KEY
8. Manual testing with sample queries

## Usage (after implementation)

```bash
uv run python main.py chat
# or
uv run python main.py chat --model gpt-4o-mini  # cheaper, faster
```
