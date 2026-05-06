"""
Intent classifier for the Nifty Sage agent.

Classifies incoming user queries into one of 7 intent types:
    comparison      → "TCS vs INFY?", "HDFC or ICICI?"
    buy_sell        → "Should I buy Reliance?", "Is TCS overvalued?"
    portfolio       → "How's my portfolio?", "What should I sell?"
    market_overview → "What sectors are trending?", "Is the market bullish?"
    rag_news        → "Why did Adani fall?", "Any news on Zomato?"
    investment_plan → "Where to invest ₹5000?", "Best monthly picks?"
    educational     → "What is PE ratio?", "Explain F&O"

Classification uses GPT-4o-mini (fast, cheap, ~10ms) with a tightly-scoped prompt.
Falls back to 'buy_sell' if classification fails.
"""

import json
import re
import time
from typing import Literal

import os

from openai import OpenAI

from utils import setup_logger

logger = setup_logger(__name__, "agent.log")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

IntentType = Literal[
    "comparison",
    "buy_sell",
    "portfolio",
    "market_overview",
    "rag_news",
    "investment_plan",
    "educational",
]

# Patterns for fast local classification (avoids an API call for obvious cases)
_LOCAL_PATTERNS: list[tuple[re.Pattern, IntentType]] = [
    # Comparison: two stock names/tickers with vs / or / compare
    (re.compile(r"\b(vs|versus|compare|between)\b", re.I), "comparison"),
    # Portfolio: my portfolio, my holdings, my concentration
    (re.compile(r"\bmy\s+(portfolio|holdings?|stocks?|positions?|concentration|allocation)\b", re.I), "portfolio"),
    (re.compile(r"\b(too\s+(much|concentrated|heavy)|overweight)\s+in\b", re.I), "portfolio"),
    (re.compile(r"\bam\s+i\s+(over|under|too)\b", re.I), "portfolio"),
    # Investment plan: invest ₹/Rs, SIP, monthly, weekly, daily
    (re.compile(r"invest\s*(₹|rs\.?|rupees?|\d)", re.I), "investment_plan"),
    (re.compile(r"\b(sip|monthly\s+invest|weekly\s+invest|daily\s+invest)\b", re.I), "investment_plan"),
    (re.compile(r"best\s+stocks?\s+(to\s+buy\s+with|for).*\b(weekly|monthly|daily|every\s+\w+)\b", re.I), "investment_plan"),
    (re.compile(r"\b(where|how)\s+(should|can|to)\s+i\s+invest\b", re.I), "investment_plan"),
    # Market overview: sectors trending, market overview
    (re.compile(r"\bsectors?\s+(trend|perform|hot|top|lead|fall)\b", re.I), "market_overview"),
    (re.compile(r"\bwhich\s+sectors?\b", re.I), "market_overview"),
    (re.compile(r"\b(the\s+market|nifty\s*\d*|sensex|market\s+(sentiment|overview|today|condition))\b", re.I), "market_overview"),
    # Educational: what is, explain, define, meaning of
    (re.compile(r"^(what\s+is|explain|define|what\s+does|meaning\s+of|how\s+does)\b", re.I), "educational"),
    # News: why did, what happened, news about
    (re.compile(r"^why\s+(did|is|are|was|were)\b", re.I), "rag_news"),
    (re.compile(r"\bnews\s+(on|about|for)\b", re.I), "rag_news"),
    (re.compile(r"\bwhat\s+happened\s+(to|with)\b", re.I), "rag_news"),
]

_SYSTEM = """\
You are a query intent classifier for an Indian stock market AI assistant.
Classify the user query into EXACTLY ONE of these intents:
- comparison: Comparing 2+ stocks (e.g., "TCS vs Infosys", "HDFC or ICICI")
- buy_sell: Asking about buying, selling, or valuation of ONE stock
- portfolio: About the user's own portfolio, holdings, or P&L
- market_overview: About the broader market, sectors, indices, or macro trends
- rag_news: Asking about news, events, or reasons for a stock/market move
- investment_plan: How/where to invest a specific amount or frequency
- educational: Asking what something means, how something works

Reply with ONLY a JSON object: {"intent": "<intent>", "confidence": <0.0-1.0>}
No explanations, no markdown, just JSON."""


def classify_intent(query: str, client: OpenAI | None = None) -> tuple[IntentType, float]:
    """
    Classify a user query into one of 7 intent types.
    Returns (intent, confidence).

    Strategy:
    1. Fast local regex check (no API call, ~0ms)
    2. GPT-4o-mini classification if no local match (reliable, ~50ms)
    """
    query = query.strip()
    if not query:
        return "buy_sell", 0.5

    # ── 1. Local fast-path ─────────────────────────────────────────────────
    # Check most specific patterns first
    # Portfolio check needs "my" to avoid matching "How is TCS portfolio?"
    for pattern, intent in _LOCAL_PATTERNS:
        if pattern.search(query):
            # Extra disambiguation for comparison vs buy_sell
            if intent == "comparison":
                # Must mention at least 2 recognizable identifiers
                # Simple heuristic: 2+ uppercase words that look like tickers OR "vs/or"
                has_vs = bool(re.search(r"\b(vs|versus)\b", query, re.I))
                has_two_caps = len(re.findall(r"\b[A-Z]{2,}\b", query)) >= 2
                if has_vs or has_two_caps:
                    logger.debug(f"Local classify '{query[:50]}' → {intent}")
                    return intent, 0.9
            else:
                logger.debug(f"Local classify '{query[:50]}' → {intent}")
                return intent, 0.9

    # ── 2. GPT-4o-mini fallback ────────────────────────────────────────────
    if client is None:
        try:
            client = OpenAI(
                api_key=GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        except Exception:
            return "buy_sell", 0.5

    try:
        t0 = time.monotonic()
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": query},
            ],
            max_tokens=60,
            temperature=0,
        )
        elapsed = time.monotonic() - t0
        raw = response.choices[0].message.content.strip()
        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match: raw = json_match.group(0)
        data = json.loads(raw)
        intent = data.get("intent", "buy_sell")
        confidence = float(data.get("confidence", 0.8))
        logger.info(f"GPT classify ({elapsed:.2f}s) '{query[:50]}' → {intent} ({confidence:.2f})")
        return intent, confidence
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        return "buy_sell", 0.5


# ── Flow-specific system prompt additions ─────────────────────────────────────

FLOW_INSTRUCTIONS: dict[IntentType, str] = {
    "comparison": """
## This is a COMPARISON query
You MUST:
1. Call `get_screener_data` for EACH stock mentioned
2. Call `compare_stocks` with all symbols
3. Produce a VERDICT using this EXACT format:

🏆 VERDICT: [STOCK A or STOCK B or NEITHER]

**Why [winner]:**
- [Key metric that makes it better: e.g., Higher ROE: 18% vs 11%]
- [Second reason]

**Why not [loser]:**
- [Key weakness]

**My recommendation:** [1-2 sentences of actionable advice with specific entry context]

⚠️ *This is analysis, not financial advice. Do your own due diligence.*
""",

    "buy_sell": """
## This is a BUY/SELL/VALUATION query
You MUST:
1. Call `get_screener_data` for the stock (PE, ROE, ROCE, promoter holding, peers)
2. Call `get_price_history` for the last 90 days (momentum, RSI, support/resistance)
3. Call `get_news` for any recent catalysts
4. End with a CLEAR verdict:

📊 RECOMMENDATION: [BUY / ACCUMULATE / HOLD / REDUCE / AVOID]

**Reasoning:** [2-3 specific data points that drive the recommendation]
**Key Risk:** [The single biggest thing that could make this wrong]
**Entry context:** [Price levels or conditions to watch if buying]

⚠️ *This is analysis, not financial advice.*
""",

    "portfolio": """
## This is a PORTFOLIO query
You MUST:
1. Call `get_portfolio_analysis` to get P&L data
2. Call `get_portfolio_risk` to get sector concentration and HHI
3. Give specific, actionable advice — not just data
4. If the user asks "what should I sell/buy", give a SPECIFIC answer

Don't just show numbers. Tell the user what to DO.
""",

    "market_overview": """
## This is a MARKET OVERVIEW query
You MUST call at least 2 of:
- `get_market_breadth` (advance/decline ratio)
- `get_sector_performance` (which sectors are up/down)
- `get_top_movers` (biggest movers today/this week)
- `get_macro_environment` (VIX, USDINR, Gold, Crude)

Synthesize into a concise market summary with a clear BULLISH / BEARISH / NEUTRAL stance.
""",

    "rag_news": """
## This is a NEWS/EVENTS query
You MUST:
1. Call `get_news` for the mentioned stock/topic
2. Call `web_search` if the news might be very recent (last 48h)
3. Summarize the key events in chronological order
4. Give context: why does this matter for the stock price?
""",

    "investment_plan": """
## This is an INVESTMENT PLAN query
You MUST:
1. Call `get_investment_plans` to see existing allocations
2. Call `get_strategy_recommendation` with the appropriate frequency
3. Call `get_portfolio_risk` if the user has a portfolio
4. Give a SPECIFIC allocation: "Put X% in A, Y% in B, Z% in C"

Include: why each pick, expected return range, and risk caveat.
""",

    "educational": """
## This is an EDUCATIONAL query
Do NOT call financial data tools unless needed to illustrate the concept with live data.
Give a clear, structured explanation:
1. **What it is** (plain English definition)
2. **Why it matters** for stock picking
3. **A concrete example** with real numbers
4. **Common misconceptions** if relevant

Keep it under 300 words. Use analogies where helpful.
""",
}


def get_flow_system_addition(intent: IntentType) -> str:
    """Get the additional system prompt instructions for a given intent."""
    return FLOW_INSTRUCTIONS.get(intent, "")
