from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class DailyStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    jobs_created: int
    jobs_expired: int
    jobs_active: int
    jobs_reposted: int
    avg_salary_eur: Optional[float] = None
    median_salary_eur: Optional[float] = None
    remote_ratio: Optional[float] = None  # 0.0–1.0


class MarketStatsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generated_at: str  # ISO 8601
    days_available: int  # actual rows returned
    chart_base_url: str  # CDN prefix, e.g. "https://cdn.openjobseu.org"
    jobs_total: int = 0  # current count of active jobs in DB
    jobs_approved: int = 0  # current count meeting feed criteria (compliance_score >= 80)


class MarketStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: MarketStatsMeta
    stats: List[DailyStats]  # 30 entries max, chronological order


class SegmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str
    jobs_active: int
    jobs_created: int
    salary_count: int = 0
    avg_salary_eur: Optional[float] = None
    median_salary_eur: Optional[float] = None


class SegmentsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generated_at: str  # ISO 8601


class SegmentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: SegmentsMeta
    segments: Dict[str, List[SegmentItem]]  # key = segment_type, value = ordered list
