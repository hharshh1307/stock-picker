"""Discovery API endpoints."""

from dataclasses import asdict
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from api_server import get_store
from discovery_engine import (
    get_all_buckets,
    get_bucket_by_id,
    get_market_pulse,
    get_movers_summary,
    get_sectors_summary,
    BucketStock,
    Bucket,
)

router = APIRouter()


def bucket_to_dict(bucket: Bucket) -> dict[str, Any]:
    """Convert a Bucket dataclass to a JSON-serializable dict."""
    return {
        "bucket_id": bucket.bucket_id,
        "name": bucket.name,
        "description": bucket.description,
        "stocks": [asdict(s) for s in bucket.stocks],
        "stock_count": len(bucket.stocks),
    }


@router.get("/market-pulse")
async def market_pulse() -> dict[str, Any]:
    """Get market pulse: breadth, sentiment, index change."""
    store = get_store()
    return get_market_pulse(store)


@router.get("/sectors")
async def sectors() -> list[dict[str, Any]]:
    """Get sector performance summary for the sector grid."""
    store = get_store()
    return get_sectors_summary(store)


@router.get("/buckets")
async def buckets(
    preview_limit: int = Query(default=6, ge=1, le=20, description="Number of stocks to preview per bucket")
) -> list[dict[str, Any]]:
    """Get all discovery buckets with preview stocks."""
    store = get_store()
    all_buckets = get_all_buckets(store)

    # Limit stocks in preview
    result = []
    for b in all_buckets:
        bucket_dict = bucket_to_dict(b)
        bucket_dict["stocks"] = bucket_dict["stocks"][:preview_limit]
        bucket_dict["preview_count"] = len(bucket_dict["stocks"])
        result.append(bucket_dict)

    return result


@router.get("/bucket/{bucket_id}")
async def bucket_detail(
    bucket_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum stocks to return")
) -> dict[str, Any]:
    """Get a specific bucket with full stock list."""
    store = get_store()
    bucket = get_bucket_by_id(store, bucket_id, limit=limit)

    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_id}' not found")

    return bucket_to_dict(bucket)


@router.get("/movers")
async def movers(
    limit: int = Query(default=10, ge=1, le=50, description="Number of movers to return")
) -> dict[str, Any]:
    """Get top gainers and losers."""
    store = get_store()
    return get_movers_summary(store, limit=limit)


@router.get("/bucket-ids")
async def bucket_ids() -> list[dict[str, str]]:
    """Get list of available bucket IDs and names."""
    return [
        {"id": "momentum_leaders", "name": "Momentum Leaders"},
        {"id": "beaten_down", "name": "Beaten Down"},
        {"id": "volume_surge", "name": "Volume Surge"},
        {"id": "revenue_rockets", "name": "Revenue Rockets"},
        {"id": "profit_machines", "name": "Profit Machines"},
        {"id": "near_52w_high", "name": "Near 52-Week High"},
        {"id": "near_52w_low", "name": "Near 52-Week Low"},
        {"id": "sector_outperformers", "name": "Sector Outperformers"},
    ]
