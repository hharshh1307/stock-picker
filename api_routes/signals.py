"""API routes for the Signal RAG pipeline."""

from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from data_store import DataStore

router = APIRouter()

def _get_store():
    from api_server import get_store
    return get_store()


# ── Input Models ──────────────────────────────────────────────────────────────

class UserActionInput(BaseModel):
    user_action: str   # APPROVED / REJECTED / SKIPPED
    user_notes: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/today")
async def get_today_signals(
    frequency: Optional[str] = None,
    store: DataStore = Depends(_get_store),
) -> Any:
    """
    Returns today's signal candidates with AI decisions and user action status.
    If frequency is specified, returns only that segment.
    """
    today = date.today().isoformat()
    query_params: list = [today]
    freq_clause = ""
    if frequency:
        freq_clause = "AND sd.frequency = ?"
        query_params.append(frequency)

    rows = store.conn.execute(
        f"""
        SELECT
            sd.id, sd.date, sd.frequency, sd.symbol,
            sc.ml_rank, sc.ml_score_1m, sc.ml_outperform_prob, sc.predicted_return_1m_pct,
            sd.ai_recommendation, sd.ai_confidence, sd.ai_reasoning,
            sd.user_action, sd.user_notes, sd.actioned_at,
            s.company_name, s.sector
        FROM signal_decisions sd
        JOIN signal_candidates sc ON sc.id = sd.candidate_id
        LEFT JOIN stocks s ON s.symbol = sd.symbol
        WHERE sd.date = ? {freq_clause}
        ORDER BY sd.frequency, sc.ml_rank
        """,
        query_params,
    ).fetchall()

    # Get latest prices in one query
    symbols = list({r["symbol"] for r in rows})
    price_map: dict[str, float] = {}
    if symbols:
        placeholders = ",".join("?" * len(symbols))
        price_rows = store.conn.execute(
            f"""
            SELECT p.symbol, p.close
            FROM prices p
            INNER JOIN (
                SELECT symbol, MAX(date) as max_date FROM prices
                WHERE symbol IN ({placeholders})
                GROUP BY symbol
            ) latest ON p.symbol = latest.symbol AND p.date = latest.max_date
            """,
            symbols,
        ).fetchall()
        price_map = {r["symbol"]: r["close"] for r in price_rows}

    grouped: dict[str, list] = {}
    for r in rows:
        freq = r["frequency"]
        if freq not in grouped:
            grouped[freq] = []
        grouped[freq].append({
            "id":                      r["id"],
            "symbol":                  r["symbol"],
            "company_name":            r["company_name"],
            "sector":                  r["sector"],
            "ml_rank":                 r["ml_rank"],
            "ml_score_1m":             r["ml_score_1m"],
            "ml_outperform_prob":      r["ml_outperform_prob"],
            "predicted_return_1m_pct": r["predicted_return_1m_pct"],
            "ai_recommendation":       r["ai_recommendation"],
            "ai_confidence":           r["ai_confidence"],
            "ai_reasoning":            r["ai_reasoning"],
            "user_action":             r["user_action"],
            "user_notes":              r["user_notes"],
            "actioned_at":             r["actioned_at"],
            "latest_price":            price_map.get(r["symbol"]),
        })

    return {
        "date": today,
        "has_signals": len(rows) > 0,
        "signals": grouped,
    }



@router.post("/run")
async def trigger_signal_pipeline(
    frequencies: Optional[list[str]] = None,
    store: DataStore = Depends(_get_store),
) -> Any:
    """
    Manually trigger the signal pipeline (ML retrieval + AI analysis).
    Runs asynchronously in a background thread.
    """
    import threading
    from signal_engine import run_daily_signal_pipeline

    def _run():
        run_daily_signal_pipeline(store)

    t = threading.Thread(target=_run, daemon=True, name="signal-pipeline")
    t.start()
    return {"status": "started", "message": "Signal pipeline running in background."}


@router.patch("/{decision_id}/action")
async def update_user_action(
    decision_id: int,
    body: UserActionInput,
    store: DataStore = Depends(_get_store),
) -> Any:
    """Record the user's APPROVED / REJECTED / SKIPPED decision on a signal."""
    valid_actions = {"APPROVED", "REJECTED", "SKIPPED"}
    action = body.user_action.upper()
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"user_action must be one of {valid_actions}")

    result = store.conn.execute(
        """
        UPDATE signal_decisions
        SET user_action = ?, user_notes = ?, actioned_at = ?
        WHERE id = ?
        """,
        (action, body.user_notes, datetime.now().isoformat(), decision_id),
    )
    store.conn.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Decision not found.")

    return {"status": "updated", "decision_id": decision_id, "user_action": action}


@router.get("/history")
async def get_signal_history(
    frequency: Optional[str] = None,
    days: int = 30,
    store: DataStore = Depends(_get_store),
) -> Any:
    """Returns past signals with their user actions and outcomes (if available)."""
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    query_params: list = [cutoff]
    if frequency:
        query_params.append(frequency)

    rows = store.conn.execute(
        f"""
        SELECT
            sd.id, sd.date, sd.frequency, sd.symbol,
            sc.ml_rank, sc.ml_outperform_prob,
            sd.ai_recommendation, sd.ai_confidence, sd.ai_reasoning,
            sd.user_action, sd.user_notes,
            so.actual_return_pct, so.nifty500_return_pct, so.alpha_pct,
            s.company_name, s.sector
        FROM signal_decisions sd
        JOIN signal_candidates sc ON sc.id = sd.candidate_id
        LEFT JOIN signal_outcomes so ON so.decision_id = sd.id
        LEFT JOIN stocks s ON s.symbol = sd.symbol
        WHERE sd.date >= ? {"AND sd.frequency = ?" if frequency else ""}
        ORDER BY sd.date DESC, sd.frequency, sc.ml_rank
        """,
        query_params,
    ).fetchall()

    return [
        {
            "id":                 r["id"],
            "date":               r["date"],
            "frequency":          r["frequency"],
            "symbol":             r["symbol"],
            "company_name":       r["company_name"],
            "sector":             r["sector"],
            "ml_rank":            r["ml_rank"],
            "ml_outperform_prob": r["ml_outperform_prob"],
            "ai_recommendation":  r["ai_recommendation"],
            "ai_confidence":      r["ai_confidence"],
            "ai_reasoning":       r["ai_reasoning"],
            "user_action":        r["user_action"],
            "user_notes":         r["user_notes"],
            "actual_return_pct":  r["actual_return_pct"],
            "nifty500_return_pct": r["nifty500_return_pct"],
            "alpha_pct":          r["alpha_pct"],
        }
        for r in rows
    ]


@router.get("/analysis")
async def get_analysis(
    lookback_days: int = 30,
    store: DataStore = Depends(_get_store),
) -> Any:
    """
    Returns pipeline performance analysis: AI accuracy, user agreement rate,
    average alpha vs Nifty 500. Triggers a fresh computation if needed.
    """
    from signal_engine import compute_analysis
    results = compute_analysis(store, lookback_days=lookback_days)
    return {"lookback_days": lookback_days, "analysis": results}


@router.post("/backfill-outcomes")
async def backfill_outcomes(store: DataStore = Depends(_get_store)) -> Any:
    """Trigger back-filling of actual returns for matured decisions."""
    from signal_engine import backfill_outcomes as _backfill
    filled = _backfill(store)
    return {"status": "done", "outcomes_filled": filled}
