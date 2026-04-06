from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Query, Response
from datetime import datetime, timezone

from storage.repositories.audit_repository import get_compliance_stats_last_7d
from storage.repositories.jobs_repository import get_jobs, get_jobs_paginated

router = APIRouter(prefix="/jobs", tags=["jobs"])

FEED_LIMIT = 200
FEED_VERSION = "v1"
FEED_MIN_COMPLIANCE_SCORE = 80


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JobItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    source: str
    source_url: str
    title: str
    company_name: str
    remote_scope: Optional[str] = None
    status: str
    first_seen_at: datetime
    last_seen_at: Optional[datetime] = None


class PaginatedJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[JobItem]
    total: int
    limit: int
    offset: int


class FeedMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generated_at: str
    count: int
    status: str
    limit: int
    version: str


class FeedJobItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    company: str
    remote_scope: Optional[str] = None
    source: str
    url: str
    first_seen_at: datetime
    status: str
    last_seen_at: Optional[datetime] = None
    description: Optional[str] = None
    source_department: Optional[str] = None
    job_family: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    salary_min_eur: Optional[int] = None
    salary_max_eur: Optional[int] = None


class FeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: FeedMeta
    jobs: List[FeedJobItem]


class ComplianceStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window: str
    total_jobs: int
    approved: int
    review: int
    rejected: int
    approved_ratio_pct: Optional[float] = None


@router.get("", response_model=PaginatedJobsResponse)
def list_jobs(
    response: Response,
    status: str | None = Query("visible"),
    q: str | None = Query(None, description="Fast fuzzy text search across title and company"),
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
    limit: int = Query(40, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000, description="Pagination offset (max 10000)"),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    items, total = get_jobs_paginated(
        status=status,
        q=q,
        company=company,
        title=title,
        source=source,
        remote_scope=remote_scope,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def serialize_feed_job(job: dict) -> dict:
    payload = {
        "id": job["job_id"],
        "title": job["title"],
        "company": job["company_name"],
        "remote_scope": job["remote_scope"],
        "source": job["source"],
        "url": job["source_url"],
        "first_seen_at": job["first_seen_at"],
        "status": job["status"],
    }

    optional_fields = [
        "last_seen_at",
        "description",
        "source_department",
        "job_family",
        "salary_min",
        "salary_max",
        "salary_currency",
        "salary_period",
        "salary_min_eur",
        "salary_max_eur",
    ]
    for field in optional_fields:
        if job.get(field) is not None:
            payload[field] = job[field]

    return payload


@router.get("/feed", response_model=FeedResponse)
def jobs_feed(response: Response):
    jobs = get_jobs(
        status="visible",
        min_compliance_score=FEED_MIN_COMPLIANCE_SCORE,
        limit=FEED_LIMIT,
        offset=0,
    )

    payload = {
        "meta": {
            "generated_at": _utc_now_iso(),
            "count": len(jobs),
            "status": "visible",
            "limit": FEED_LIMIT,
            "version": FEED_VERSION,
        },
        "jobs": [serialize_feed_job(job) for job in jobs],
    }

    response.headers["Cache-Control"] = "public, max-age=300"
    return payload


@router.get("/stats/compliance-7d", response_model=ComplianceStatsResponse)
def jobs_compliance_stats_7d(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    return get_compliance_stats_last_7d()
