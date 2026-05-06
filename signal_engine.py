"""
signal_engine.py — RAG-style signal pipeline.

Architecture:
  Retrieval:   ML ranks all Nifty 500 stocks → top-K per frequency segment
  Generation:  AI agent deep-analyses each of the top-K → BUY / HOLD / SKIP
  Feedback:    User approves/rejects → stored in signal_decisions
  Outcomes:    After holding period, actual returns back-filled → signal_outcomes
  Analysis:    Recall@K, AI accuracy, alpha vs Nifty 500 computed periodically

Designed to run daily at ~17:00 IST (after price refresh + ML retrain).
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from data_store import DataStore

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

# Top-K per frequency (ML retrieval step)
TOP_K: dict[str, int] = {
    "Daily":     10,
    "Weekly":    15,
    "Monthly":   20,
    "Yearly":    25,
    "Long-term": 25,
}

# Holding period in trading days (for outcome recording)
HOLDING_DAYS: dict[str, int] = {
    "Daily":     1,
    "Weekly":    5,
    "Monthly":   20,
    "Yearly":    252,
    "Long-term": 252,
}

FREQUENCIES = list(TOP_K.keys())


# ── ML Retrieval ──────────────────────────────────────────────────────────────

def retrieve_top_k(store: DataStore, frequency: str, run_date: date) -> list[dict]:
    """
    Step 1 — Retrieval: load ML predictions and return top-K candidates
    for the given frequency, ranked by the frequency-appropriate ML score.

    Frequency → ML score used:
      Daily     → ml_1d_score  (short-term momentum)
      Weekly    → ml_1w_score
      Monthly   → ml_1m_score  + outperform_probability
      Yearly    → ml_1m_score  + outperform_probability (no 1y ML model yet)
      Long-term → ml_1m_score  + outperform_probability (fundamental bias)
    """
    from ml_pipeline import get_ml_predictions
    preds = get_ml_predictions()

    if not preds:
        logger.warning("No ML predictions available. Run ml_pipeline.train_models() first.")
        return []

    k = TOP_K.get(frequency, 15)

    # Select the primary score key per frequency
    score_key_map = {
        "Daily":     "ml_1d_score",
        "Weekly":    "ml_1w_score",
        "Monthly":   "ml_1m_score",
        "Yearly":    "ml_1m_score",
        "Long-term": "ml_1m_score",
    }
    primary_key = score_key_map.get(frequency, "ml_1m_score")

    # Weight: primary score 70%, outperform probability 30%
    # For Daily/Weekly: outperform_prob is still a useful quality filter
    scored = []
    for symbol, p in preds.items():
        primary = (p.get(primary_key) or 0) / 100   # normalise to 0-1
        outprob = (p.get("outperform_probability") or 0)

        # For longer horizons, weight outperform prob more heavily
        if frequency in ("Yearly", "Long-term"):
            composite = primary * 0.4 + outprob * 0.6
        elif frequency == "Monthly":
            composite = primary * 0.6 + outprob * 0.4
        else:  # Daily / Weekly — momentum dominates
            composite = primary * 0.8 + outprob * 0.2

        scored.append({
            "symbol":                  symbol,
            "ml_score_1m":             p.get("ml_1m_score"),
            "ml_outperform_prob":      p.get("outperform_probability"),
            "predicted_return_1m_pct": p.get("predicted_return_1m"),
            f"ml_{primary_key}":       p.get(primary_key),  # expose the score used
            "composite":               composite,
        })

    scored.sort(key=lambda x: x["composite"], reverse=True)

    # Filter to only symbols that exist in the stocks table (FK constraint)
    known_symbols = {
        r["symbol"]
        for r in store.conn.execute("SELECT symbol FROM stocks").fetchall()
    }
    scored = [s for s in scored if s["symbol"] in known_symbols]

    top_k = scored[:k]

    # Clear existing candidates (and their decisions) for this date+frequency
    # Must delete child (decisions) before parent (candidates)
    store.conn.execute(
        """DELETE FROM signal_decisions WHERE date = ? AND frequency = ?""",
        (run_date.isoformat(), frequency),
    )
    store.conn.execute(
        "DELETE FROM signal_candidates WHERE date = ? AND frequency = ?",
        (run_date.isoformat(), frequency),
    )

    # Persist candidates to DB
    for rank, item in enumerate(top_k, start=1):
        store.conn.execute(
            """
            INSERT INTO signal_candidates
                (date, frequency, symbol, ml_rank, ml_score_1m,
                 ml_outperform_prob, predicted_return_1m_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_date.isoformat(),
                frequency,
                item["symbol"],
                rank,
                item["ml_score_1m"],
                item["ml_outperform_prob"],
                item["predicted_return_1m_pct"],
            ),
        )

    store.conn.commit()
    logger.info(f"[{frequency}] Saved {len(top_k)} candidates (ranked by {primary_key}).")
    return top_k




# ── AI Analysis ───────────────────────────────────────────────────────────────

def _build_stock_context(store: DataStore, symbol: str) -> str:
    """Gather a compact context block for the AI to analyse."""
    lines = [f"## {symbol}"]

    # Basic info
    stock = store.get_stock(symbol)
    if stock:
        lines.append(f"Company: {stock.company_name}  |  Sector: {stock.sector}")

    # Latest price + 30d + 52w
    latest = store.conn.execute(
        "SELECT close, date FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if latest:
        lines.append(f"LTP: ₹{latest['close']:.2f} (as of {latest['date']})")

    p30 = store.conn.execute(
        "SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1",
        (symbol, (date.today() - timedelta(days=30)).isoformat()),
    ).fetchone()
    if p30 and latest:
        chg30 = ((latest["close"] - p30["close"]) / p30["close"]) * 100
        lines.append(f"30d change: {chg30:+.1f}%")

    w52 = store.conn.execute(
        "SELECT MIN(low) as lo, MAX(high) as hi FROM prices WHERE symbol = ? AND date >= ?",
        (symbol, (date.today() - timedelta(days=365)).isoformat()),
    ).fetchone()
    if w52 and w52["hi"]:
        lines.append(f"52w range: ₹{w52['lo']:.0f} – ₹{w52['hi']:.0f}")

    # Recent news headlines (last 5)
    news = store.conn.execute(
        "SELECT title, source_name, published_at FROM news WHERE symbol = ? ORDER BY published_at DESC LIMIT 5",
        (symbol,),
    ).fetchall()
    if news:
        lines.append("Recent news:")
        for n in news:
            lines.append(f"  • [{n['source_name']}] {n['title']}")

    return "\n".join(lines)


def analyse_candidates_with_ai(
    store: DataStore,
    candidates: list[dict],
    frequency: str,
    run_date: date,
) -> list[dict]:
    """
    Step 2 — Generation: call the AI agent to analyse each candidate.
    Returns list of decisions with ai_recommendation, ai_confidence, ai_reasoning.
    """
    import os
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()

    client = OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    decisions = []
    for candidate in candidates:
        symbol = candidate["symbol"]
        context = _build_stock_context(store, symbol)

        system_prompt = f"""You are a disciplined Indian equity analyst. 
Today is {run_date.isoformat()}. You are evaluating a stock for a **{frequency}** investment strategy.
The ML model has flagged this stock as a top candidate with:
- 1-month outperformance probability: {candidate.get('ml_outperform_prob', 'N/A')}
- Predicted 1-month return: {candidate.get('predicted_return_1m_pct', 'N/A')}%

Your job: analyse the stock and make ONE of: BUY / HOLD / SKIP.
- BUY: strong conviction this stock will outperform Nifty 500 over the {frequency} period
- HOLD: uncertain, monitoring
- SKIP: negative signals outweigh the ML optimism

Respond ONLY as valid JSON:
{{"recommendation": "BUY|HOLD|SKIP", "confidence": 0.0-1.0, "reasoning": "2-3 sentences max"}}"""

        try:
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200,
            )
            raw_content = response.choices[0].message.content.strip()
            import re
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                raw_content = json_match.group(0)
            parsed = json.loads(raw_content)
            rec  = parsed.get("recommendation", "SKIP").upper()
            conf = float(parsed.get("confidence", 0.5))
            reas = parsed.get("reasoning", "")
        except Exception as e:
            raw_c = getattr(response.choices[0].message, 'content', 'None') if 'response' in locals() else 'No response'
            logger.warning(f"AI analysis failed for {symbol}: {e}. RAW: {repr(raw_c)}")
            rec, conf, reas = "SKIP", 0.0, f"AI analysis error: {e}"

        decisions.append({
            "symbol":             symbol,
            "frequency":          frequency,
            "date":               run_date.isoformat(),
            "ml_rank":            candidate.get("ml_rank", 0),
            "ml_outperform_prob": candidate.get("ml_outperform_prob"),
            "ai_recommendation":  rec,
            "ai_confidence":      round(conf, 3),
            "ai_reasoning":       reas,
        })
        logger.info(f"  {symbol}: {rec} (conf={conf:.2f})")

    return decisions


def save_decisions(store: DataStore, decisions: list[dict]) -> None:
    """Persist AI decisions to signal_decisions, linked to signal_candidates."""
    for d in decisions:
        # Fetch the candidate ID
        row = store.conn.execute(
            "SELECT id FROM signal_candidates WHERE date = ? AND frequency = ? AND symbol = ?",
            (d["date"], d["frequency"], d["symbol"]),
        ).fetchone()
        if not row:
            continue
        store.conn.execute(
            """
            INSERT OR IGNORE INTO signal_decisions
                (candidate_id, date, frequency, symbol,
                 ai_recommendation, ai_confidence, ai_reasoning, user_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (
                row["id"], d["date"], d["frequency"], d["symbol"],
                d["ai_recommendation"], d["ai_confidence"], d["ai_reasoning"],
            ),
        )
    store.conn.commit()
    logger.info(f"Saved {len(decisions)} decisions to DB.")


# ── Full Daily Pipeline ────────────────────────────────────────────────────────

def run_daily_signal_pipeline(store: Optional[DataStore] = None) -> dict:
    """
    Run the full pipeline for all frequency segments:
      1. ML retrieval → top-K candidates
      2. AI analysis → BUY/HOLD/SKIP per candidate
      3. Save to DB (user_action = PENDING)

    Returns summary dict with counts per frequency.
    """
    if store is None:
        store = DataStore()

    today = date.today()
    summary = {}

    for frequency in FREQUENCIES:
        logger.info(f"\n{'='*50}\n[{frequency}] Starting signal pipeline...\n{'='*50}")

        # Step 1: ML retrieval
        candidates = retrieve_top_k(store, frequency, today)
        if not candidates:
            summary[frequency] = {"error": "No ML predictions available"}
            continue

        # Step 2: AI analysis
        decisions = analyse_candidates_with_ai(store, candidates, frequency, today)

        # Step 3: Save
        save_decisions(store, decisions)

        buys  = sum(1 for d in decisions if d["ai_recommendation"] == "BUY")
        holds = sum(1 for d in decisions if d["ai_recommendation"] == "HOLD")
        skips = sum(1 for d in decisions if d["ai_recommendation"] == "SKIP")

        summary[frequency] = {
            "candidates": len(candidates),
            "decisions":  len(decisions),
            "BUY": buys, "HOLD": holds, "SKIP": skips,
        }
        logger.info(f"[{frequency}] Done. BUY={buys} HOLD={holds} SKIP={skips}")

    return {"date": today.isoformat(), "frequencies": summary}


# ── Outcome Back-Filling ───────────────────────────────────────────────────────

def backfill_outcomes(store: Optional[DataStore] = None) -> int:
    """
    For each APPROVED decision where the holding period has elapsed,
    compute actual return and alpha vs Nifty 500. Run daily.
    """
    if store is None:
        store = DataStore()

    today = date.today()
    filled = 0

    # Find approved decisions without outcomes yet
    pending = store.conn.execute(
        """
        SELECT sd.id, sd.date, sd.frequency, sd.symbol
        FROM signal_decisions sd
        LEFT JOIN signal_outcomes so ON so.decision_id = sd.id
        WHERE sd.user_action = 'APPROVED' AND so.id IS NULL
        """,
    ).fetchall()

    for row in pending:
        holding_days = HOLDING_DAYS.get(row["frequency"], 20)
        decision_date = date.fromisoformat(row["date"])
        outcome_date = decision_date + timedelta(days=holding_days)

        if outcome_date > today:
            continue  # Holding period not over yet

        # Get prices at entry and exit
        entry = store.conn.execute(
            "SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1",
            (row["symbol"], row["date"]),
        ).fetchone()
        exit_ = store.conn.execute(
            "SELECT close FROM prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 1",
            (row["symbol"], outcome_date.isoformat()),
        ).fetchone()

        if not entry or not exit_:
            continue

        actual_ret = (exit_["close"] - entry["close"]) / entry["close"] * 100

        # Nifty 500 return over same period
        idx_entry = store.conn.execute(
            "SELECT close FROM index_data WHERE date >= ? ORDER BY date ASC LIMIT 1",
            (row["date"],),
        ).fetchone()
        idx_exit = store.conn.execute(
            "SELECT close FROM index_data WHERE date >= ? ORDER BY date ASC LIMIT 1",
            (outcome_date.isoformat(),),
        ).fetchone()

        nifty_ret = None
        alpha = None
        if idx_entry and idx_exit:
            nifty_ret = (idx_exit["close"] - idx_entry["close"]) / idx_entry["close"] * 100
            alpha = actual_ret - nifty_ret

        store.conn.execute(
            """
            INSERT OR IGNORE INTO signal_outcomes
                (decision_id, actual_return_pct, nifty500_return_pct, alpha_pct, outcome_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (row["id"], round(actual_ret, 3),
             round(nifty_ret, 3) if nifty_ret else None,
             round(alpha, 3) if alpha else None,
             outcome_date.isoformat()),
        )
        filled += 1

    store.conn.commit()
    logger.info(f"Back-filled {filled} outcomes.")
    return filled


# ── Analysis ───────────────────────────────────────────────────────────────────

def compute_analysis(store: Optional[DataStore] = None, lookback_days: int = 30) -> list[dict]:
    """
    Compute pipeline performance metrics for all frequencies over the lookback window.
    Saves results to signal_analysis table and returns them.
    """
    if store is None:
        store = DataStore()

    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    results = []

    for frequency in FREQUENCIES:
        k = TOP_K[frequency]

        # Recall@K: what % of top-10 performers (by actual return) appeared in our top-K?
        # We check: among stocks that actually outperformed Nifty 500 in period,
        # how many were in our candidate set?
        total_approved = store.conn.execute(
            """SELECT COUNT(*) as n FROM signal_decisions
               WHERE frequency = ? AND date >= ? AND user_action = 'APPROVED'""",
            (frequency, cutoff),
        ).fetchone()["n"]

        profitable_approved = store.conn.execute(
            """SELECT COUNT(*) as n
               FROM signal_decisions sd
               JOIN signal_outcomes so ON so.decision_id = sd.id
               WHERE sd.frequency = ? AND sd.date >= ?
               AND sd.user_action = 'APPROVED' AND so.actual_return_pct > 0""",
            (frequency, cutoff),
        ).fetchone()["n"]

        ai_buys = store.conn.execute(
            """SELECT COUNT(*) as n FROM signal_decisions
               WHERE frequency = ? AND date >= ? AND ai_recommendation = 'BUY'""",
            (frequency, cutoff),
        ).fetchone()["n"]

        user_approved_of_buys = store.conn.execute(
            """SELECT COUNT(*) as n FROM signal_decisions
               WHERE frequency = ? AND date >= ? AND ai_recommendation = 'BUY'
               AND user_action = 'APPROVED'""",
            (frequency, cutoff),
        ).fetchone()["n"]

        avg_alpha_row = store.conn.execute(
            """SELECT AVG(so.alpha_pct) as avg_alpha
               FROM signal_decisions sd
               JOIN signal_outcomes so ON so.decision_id = sd.id
               WHERE sd.frequency = ? AND sd.date >= ? AND sd.user_action = 'APPROVED'""",
            (frequency, cutoff),
        ).fetchone()

        ai_accuracy = (profitable_approved / total_approved) if total_approved > 0 else None
        user_agreement = (user_approved_of_buys / ai_buys) if ai_buys > 0 else None
        avg_alpha = avg_alpha_row["avg_alpha"] if avg_alpha_row and avg_alpha_row["avg_alpha"] else None

        row = {
            "frequency":          frequency,
            "lookback_days":      lookback_days,
            "ai_accuracy":        round(ai_accuracy, 3) if ai_accuracy else None,
            "user_agreement_rate": round(user_agreement, 3) if user_agreement else None,
            "avg_alpha_pct":      round(avg_alpha, 3) if avg_alpha else None,
            "sample_size":        total_approved,
        }
        results.append(row)

        # Save to DB
        store.conn.execute(
            """
            INSERT OR REPLACE INTO signal_analysis
                (analysis_date, frequency, lookback_days,
                 ai_accuracy, user_agreement_rate, avg_alpha_pct, sample_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date.today().isoformat(), frequency, lookback_days,
             row["ai_accuracy"], row["user_agreement_rate"],
             row["avg_alpha_pct"], row["sample_size"]),
        )

    store.conn.commit()
    return results


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    result = run_daily_signal_pipeline()
    print(json.dumps(result, indent=2))
