"""Admin API routes — pipeline control, data refresh, system stats.
Only accessible when the frontend passes the admin token (enforced by Next.js middleware).
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException

router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_API_TOKEN", "niftysage-admin-2025")
PROJECT_ROOT = Path(__file__).parent


def _require_admin(x_admin_token: str | None):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required")


# ── System Stats ────────────────────────────────────────────────────────────

@router.get("/stats")
async def system_stats(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Return DB table counts, last fetch times, cache status."""
    _require_admin(x_admin_token)

    from api_server import get_store
    store = get_store()

    tables = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    table_counts = {}
    for t in tables:
        name = t["name"]
        try:
            count = store.conn.execute(f"SELECT COUNT(*) as n FROM {name}").fetchone()["n"]
            table_counts[name] = count
        except Exception:
            table_counts[name] = -1

    # Latest price date
    latest_price = store.conn.execute(
        "SELECT MAX(date) as d FROM prices"
    ).fetchone()["d"]

    # Latest news date
    latest_news = store.conn.execute(
        "SELECT MAX(published_at) as d FROM news"
    ).fetchone()["d"]

    # Embedding file info
    data_dir = Path("data")
    embedding_file = data_dir / "stock_embeddings.json"
    embedding_info = None
    if embedding_file.exists():
        stat = embedding_file.stat()
        embedding_info = {
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    # Fetch log
    try:
        fetch_log = store.conn.execute(
            "SELECT * FROM fetch_log ORDER BY last_run DESC LIMIT 10"
        ).fetchall()
        fetch_log = [dict(r) for r in fetch_log]
    except Exception:
        fetch_log = []

    # Screener cache count
    screener_count = 0
    try:
        screener_count = store.conn.execute(
            "SELECT COUNT(*) as n FROM screener_cache"
        ).fetchone()["n"]
    except Exception:
        pass

    # Discovery bucket cache status
    from api_routes.discovery import _buckets_cache
    cache_status = {
        "has_data": _buckets_cache["data"] is not None,
        "expires_at": datetime.fromtimestamp(_buckets_cache["expires_at"]).isoformat()
        if _buckets_cache["expires_at"] > 0
        else None,
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "database": {
            "table_counts": table_counts,
            "latest_price_date": latest_price,
            "latest_news_date": latest_news,
            "screener_cache_entries": screener_count,
        },
        "embeddings": embedding_info,
        "fetch_log": fetch_log,
        "discovery_cache": cache_status,
    }


@router.get("/logs")
async def get_logs(
    log_file: str = "server_err.log",
    lines: int = 100,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Return last N lines of a log file."""
    _require_admin(x_admin_token)

    log_path = PROJECT_ROOT / "logs" / log_file
    if not log_path.exists():
        return {"lines": [], "error": f"Log file {log_file} not found"}

    # Available log files
    available = [f.name for f in (PROJECT_ROOT / "logs").glob("*.log")]

    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_path)],
            capture_output=True, text=True, timeout=5
        )
        log_lines = result.stdout.splitlines()
    except Exception as e:
        log_lines = [f"Error reading log: {e}"]

    return {"file": log_file, "lines": log_lines, "available_files": available}


@router.get("/git")
async def git_status(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Return git status: branch, last 10 commits, dirty files."""
    _require_admin(x_admin_token)

    def run(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=PROJECT_ROOT)
            return r.stdout.strip()
        except Exception:
            return ""

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commits = run(["git", "log", "--oneline", "-10"])
    dirty = run(["git", "status", "--short"])
    remote = run(["git", "remote", "-v"])

    return {
        "branch": branch,
        "recent_commits": commits.splitlines() if commits else [],
        "dirty_files": dirty.splitlines() if dirty else [],
        "remote": remote.splitlines()[0] if remote else None,
    }


# ── Pipeline Actions ─────────────────────────────────────────────────────────

_running_jobs: dict[str, dict] = {}


def _run_job_async(job_id: str, cmd: list[str], cwd: str = None):
    """Run a shell command asynchronously and track its status."""
    _running_jobs[job_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "cmd": " ".join(cmd),
        "output": [],
    }

    def target():
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=cwd or PROJECT_ROOT
            )
            for line in process.stdout:
                _running_jobs[job_id]["output"].append(line.rstrip())
                # Keep only last 200 lines in memory
                if len(_running_jobs[job_id]["output"]) > 200:
                    _running_jobs[job_id]["output"] = _running_jobs[job_id]["output"][-200:]
            process.wait()
            _running_jobs[job_id]["status"] = "done" if process.returncode == 0 else "error"
            _running_jobs[job_id]["return_code"] = process.returncode
            _running_jobs[job_id]["finished_at"] = datetime.now().isoformat()
        except Exception as e:
            _running_jobs[job_id]["status"] = "error"
            _running_jobs[job_id]["error"] = str(e)
            _running_jobs[job_id]["finished_at"] = datetime.now().isoformat()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()


@router.post("/action/refresh-prices")
async def refresh_prices(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    job_id = f"refresh-prices-{int(time.time())}"
    _run_job_async(job_id, ["uv", "run", "python", "main.py", "prices"])
    return {"job_id": job_id, "status": "started"}


@router.post("/action/refresh-financials")
async def refresh_financials(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    job_id = f"refresh-financials-{int(time.time())}"
    _run_job_async(job_id, ["uv", "run", "python", "main.py", "financials"])
    return {"job_id": job_id, "status": "started"}


@router.post("/action/refresh-news")
async def refresh_news(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    job_id = f"refresh-news-{int(time.time())}"
    _run_job_async(job_id, ["uv", "run", "python", "main.py", "news"])
    return {"job_id": job_id, "status": "started"}


@router.post("/action/run-signals")
async def run_signals(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    job_id = f"run-signals-{int(time.time())}"
    _run_job_async(job_id, [
        "uv", "run", "python", "-c",
        "from signal_engine import run_daily_signal_pipeline; run_daily_signal_pipeline()"
    ])
    return {"job_id": job_id, "status": "started"}


@router.post("/action/rebuild-embeddings")
async def rebuild_embeddings(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    job_id = f"rebuild-embeddings-{int(time.time())}"
    _run_job_async(job_id, [
        "uv", "run", "python", "-c",
        "from embedding_search import update_embeddings_incremental; update_embeddings_incremental()"
    ])
    return {"job_id": job_id, "status": "started"}


@router.post("/action/clear-discovery-cache")
async def clear_discovery_cache(x_admin_token: str | None = Header(default=None)) -> dict:
    _require_admin(x_admin_token)
    from api_routes.discovery import _buckets_cache
    _buckets_cache["data"] = None
    _buckets_cache["expires_at"] = 0.0
    return {"status": "cleared", "timestamp": datetime.now().isoformat()}


@router.post("/action/run-full-pipeline")
async def run_full_pipeline(x_admin_token: str | None = Header(default=None)) -> dict:
    """Run prices → signals → embedding update in sequence."""
    _require_admin(x_admin_token)
    job_id = f"full-pipeline-{int(time.time())}"
    _run_job_async(job_id, ["uv", "run", "python", "main.py", "all"])
    return {"job_id": job_id, "status": "started"}


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    x_admin_token: str | None = Header(default=None),
) -> dict:
    _require_admin(x_admin_token)
    if job_id not in _running_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _running_jobs[job_id]


@router.get("/jobs")
async def list_jobs(x_admin_token: str | None = Header(default=None)) -> list[dict]:
    _require_admin(x_admin_token)
    return [
        {"job_id": jid, "status": j["status"], "cmd": j["cmd"],
         "started_at": j["started_at"], "finished_at": j.get("finished_at")}
        for jid, j in sorted(_running_jobs.items(), key=lambda x: x[1]["started_at"], reverse=True)
    ]
