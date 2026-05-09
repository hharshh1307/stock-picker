"""FastAPI server for the Stock Picker Discovery & Chat API."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import DB_PATH
from data_store import DataStore

# Global store instance
store: DataStore | None = None


def get_store() -> DataStore:
    """Get the global DataStore instance."""
    if store is None:
        raise RuntimeError("DataStore not initialized. Server not properly started.")
    return store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DataStore lifecycle and background price scheduler."""
    global store
    import logging
    logger = logging.getLogger(__name__)

    # Ensure data directory exists (Railway volume mount)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using database at: {DB_PATH}")

    store = DataStore(db_path=str(DB_PATH))
    logger.info("DataStore initialized successfully")

    # Start the daily price freshness scheduler (non-fatal if it fails)
    scheduler = None
    try:
        from price_scheduler import start_scheduler
        scheduler = start_scheduler(store)
        logger.info("Price scheduler started")
    except Exception as e:
        logger.warning(f"Price scheduler failed to start (non-fatal): {e}")

    yield

    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    if store:
        store.close()
        store = None


app = FastAPI(
    title="Stock Picker API",
    description="Discovery buckets, stock data, and AI chat for Nifty 500 stocks",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend (allow Vercel deployments)
import os

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add production frontend URL from environment
if frontend_url := os.getenv("FRONTEND_URL"):
    ALLOWED_ORIGINS.append(frontend_url)

# Allow all Vercel preview deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, Any]:
    """Health check and API info."""
    return {
        "status": "ok",
        "api": "Stock Picker",
        "version": "1.0.0",
        "endpoints": {
            "discovery": "/api/discovery/*",
            "stocks": "/api/stocks/*",
            "chat": "/api/chat",
            "user": "/api/user/*",
        },
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from api_routes import discovery, stocks, chat, user, signals, admin, auth

app.include_router(discovery.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


def run_server(host: str = "0.0.0.0", port: int | None = None, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn
    # Use PORT env var (for Railway/Render) or default to 8000
    actual_port = port or int(os.getenv("PORT", 8000))
    uvicorn.run(
        "api_server:app",
        host=host,
        port=actual_port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
