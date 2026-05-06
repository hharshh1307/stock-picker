"""
price_scheduler.py — Automatic daily price freshness pipeline.

Strategy:
  • On server startup: check if DB prices are stale (last date < today/last trading day).
    If stale, run an incremental refresh immediately in a background thread.
  • Daily at 16:00 IST (after NSE market close at 15:30): run incremental refresh.
  • Weekends: market is closed, skip.

This runs entirely in-process via APScheduler — no external cron or worker needed.
"""

import logging
import threading
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# IST is UTC+5:30
IST_OFFSET_HOURS = 5
IST_OFFSET_MINUTES = 30

# Trigger time: 16:00 IST = 10:30 UTC
DAILY_TRIGGER_HOUR_UTC = 10
DAILY_TRIGGER_MINUTE_UTC = 30


def _is_trading_day(d: date) -> bool:
    """Returns True if the date is a weekday (Mon–Fri). Does not check NSE holidays."""
    return d.weekday() < 5  # 0=Mon, 4=Fri


def _last_trading_day() -> date:
    """Returns the most recent trading day (today if weekday and after 3:45 PM IST, else previous weekday)."""
    now_ist = datetime.utcnow() + timedelta(hours=IST_OFFSET_HOURS, minutes=IST_OFFSET_MINUTES)
    d = now_ist.date()
    # If it's before market close (15:45 IST), use the previous trading day
    market_close_ist = now_ist.replace(hour=15, minute=45, second=0, microsecond=0)
    if now_ist < market_close_ist:
        d -= timedelta(days=1)
    # Walk back to last weekday
    while not _is_trading_day(d):
        d -= timedelta(days=1)
    return d


def _prices_are_stale(store) -> bool:
    """Check if the most common latest price date across all stocks is behind the last trading day."""
    try:
        # Sample the latest price date across a broad set of stocks for speed
        row = store.conn.execute(
            """
            SELECT MAX(date) as max_date
            FROM (
                SELECT MAX(date) as date
                FROM prices
                GROUP BY symbol
                LIMIT 50
            )
            """
        ).fetchone()
        if not row or not row["max_date"]:
            logger.info("No price data in DB — prices are stale.")
            return True
        latest_in_db = date.fromisoformat(row["max_date"])
        last_trading = _last_trading_day()
        is_stale = latest_in_db < last_trading
        if is_stale:
            logger.info(f"Prices stale: DB has {latest_in_db}, last trading day is {last_trading}.")
        else:
            logger.info(f"Prices fresh: DB has {latest_in_db}, last trading day is {last_trading}.")
        return is_stale
    except Exception as e:
        logger.warning(f"Stale check failed: {e}")
        return False  # Don't refresh if we can't determine staleness


def _run_price_refresh(store) -> int:
    """Run incremental price refresh. Returns number of new records inserted."""
    try:
        import fetch_price_data
        logger.info("🔄 Starting daily price refresh...")
        result = fetch_price_data.run(store, full_refresh=False)
        new_records = result.get("records", 0)
        logger.info(
            f"✅ Daily price refresh done: "
            f"{result.get('success', 0)}/{result.get('total', 0)} stocks, "
            f"{new_records} new records."
        )
        return new_records
    except Exception as e:
        logger.error(f"❌ Daily price refresh failed: {e}", exc_info=True)
        return 0


def _run_model_retrain(store) -> bool:
    """Retrain ML models after a price refresh. Returns True on success."""
    try:
        from ml_pipeline import train_models
        logger.info("🤖 Starting ML model retrain...")
        result = train_models(store)
        metrics = result.get("metrics", [])
        for m in metrics:
            if "R2" in m:
                logger.info(f"  [{m['model']}] R2={m['R2']}  MAE={m['MAE']}")
            elif "roc_auc" in m:
                logger.info(f"  [{m['model']}] AUC={m['roc_auc']}  Acc={m['accuracy']}")
        logger.info(f"✅ ML retrain complete. {result.get('stocks_with_predictions', 0)} stocks scored.")
        return True
    except Exception as e:
        logger.error(f"❌ ML retrain failed: {e}", exc_info=True)
        return False


def _run_signal_pipeline(store):
    """Run the daily RAG signal pipeline for all frequency segments."""
    try:
        from signal_engine import run_daily_signal_pipeline
        logger.info("📡 Starting daily signal pipeline...")
        result = run_daily_signal_pipeline(store)
        freqs = result.get("frequencies", {})
        for freq, summary in freqs.items():
            if "error" not in summary:
                logger.info(
                    f"  [{freq}] candidates={summary['candidates']} "
                    f"BUY={summary['BUY']} HOLD={summary['HOLD']} SKIP={summary['SKIP']}"
                )
        logger.info("✅ Signal pipeline complete.")
    except Exception as e:
        logger.error(f"❌ Signal pipeline failed: {e}", exc_info=True)


def _run_price_refresh_background(store, trigger_retrain: bool = True):
    """
    Spawn a daemon thread that runs the full daily pipeline:
      1. Incremental price refresh
      2. ML retrain (if >= 50 new records)
      3. Signal pipeline (ML retrieval + AI analysis for all frequencies)
    """
    def _worker():
        new_records = _run_price_refresh(store)
        retrained = False
        if trigger_retrain and new_records >= 50:
            logger.info(f"{new_records} new price records → triggering ML retrain.")
            retrained = _run_model_retrain(store)
        elif trigger_retrain:
            logger.info(f"Only {new_records} new records — skipping ML retrain.")

        # Always run signal pipeline after refresh (uses latest predictions)
        logger.info("Running signal pipeline after price refresh.")
        _run_signal_pipeline(store)

    t = threading.Thread(target=_worker, daemon=True, name="price-refresh")
    t.start()
    logger.info("Price refresh + signal pipeline thread started.")


def start_scheduler(store):
    """
    Start the APScheduler background scheduler.
    - Immediately checks staleness and refreshes if needed.
    - Schedules daily refresh at 16:00 IST (10:30 UTC) on weekdays.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed — automatic price refresh disabled. "
            "Install with: uv add apscheduler"
        )
        return None

    scheduler = BackgroundScheduler(daemon=True)

    # ── Job 1: 16:00 IST (10:30 UTC) — price refresh + ML retrain + signals ────
    scheduler.add_job(
        func=lambda: _run_price_refresh_background(store),
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=DAILY_TRIGGER_HOUR_UTC,
            minute=DAILY_TRIGGER_MINUTE_UTC,
            timezone="UTC",
        ),
        id="daily_price_refresh",
        name="Daily Pipeline (16:00 IST): prices → ML → signals",
        replace_existing=True,
    )

    # ── Job 2: 17:30 IST (12:00 UTC) — re-run signals only (backup) ───────────
    # Ensures signals are always fresh even if the 16:00 job ran without retrain
    scheduler.add_job(
        func=lambda: _run_signal_pipeline(store),
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=12,
            minute=0,
            timezone="UTC",
        ),
        id="daily_signal_refresh",
        name="Daily Signals Refresh (17:30 IST)",
        replace_existing=True,
    )

    # ── Job 3: outcome backfill — runs at 18:00 IST (12:30 UTC) daily ─────────
    scheduler.add_job(
        func=lambda: __import__('signal_engine').backfill_outcomes(store),
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=12,
            minute=30,
            timezone="UTC",
        ),
        id="daily_outcome_backfill",
        name="Daily Outcome Backfill (18:00 IST)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Price scheduler started. Daily refresh at {DAILY_TRIGGER_HOUR_UTC:02d}:{DAILY_TRIGGER_MINUTE_UTC:02d} UTC "
        f"(16:00 IST) on weekdays."
    )

    # ── Startup stale check: refresh immediately if DB is behind ─────────────
    if _prices_are_stale(store):
        logger.info("Prices are stale on startup — triggering immediate background refresh.")
        _run_price_refresh_background(store)
    else:
        logger.info("Prices are up-to-date. No startup refresh needed.")

    return scheduler
