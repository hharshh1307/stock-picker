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
    """Manage DataStore lifecycle."""
    global store
    store = DataStore(db_path=str(DB_PATH))
    yield
    if store:
        store.close()
        store = None


app = FastAPI(
    title="Stock Picker API",
    description="Discovery buckets, stock data, and AI chat for Nifty 500 stocks",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
        },
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from api_routes import discovery, stocks, chat

app.include_router(discovery.router, prefix="/api/discovery", tags=["discovery"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
