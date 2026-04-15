from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from app.workers.market_types import DailyStats, SegmentItem
from storage.db_engine import get_engine
from storage.repositories.market_repository import get_market_daily_stats
from storage.repositories.market_segments_repository import get_market_segments_snapshot

router = APIRouter(prefix="/analytics", tags=["paid-api-v1"])


class MarketAnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int
    count: int
    data: list[DailyStats]


class SegmentsAnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int
    data: list[SegmentItem]


@router.get("/market", response_model=MarketAnalyticsResponse)
def get_market_analytics(days: int = Query(30, ge=1, le=365)):
    """Return daily market stats for the last N days.

    Args:
        days: Number of days to return (1–365, default 30).
    """
    with get_engine().connect() as conn:
        data = get_market_daily_stats(conn, days=days)
    return {"days": days, "count": len(data), "data": data}


@router.get("/segments", response_model=SegmentsAnalyticsResponse)
def get_segment_analytics():
    """Return the most recent market snapshot broken down by segment type."""
    with get_engine().connect() as conn:
        raw = get_market_segments_snapshot(conn)
    data = [
        SegmentItem(
            value=row["segment_value"],
            jobs_active=row["jobs_active"],
            jobs_created=row["jobs_created"],
            avg_salary_eur=row["avg_salary_eur"],
            median_salary_eur=row["median_salary_eur"],
        )
        for row in raw
    ]
    return {"count": len(data), "data": data}
