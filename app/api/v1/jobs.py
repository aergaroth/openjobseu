from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from storage.repositories.paid_api_repository import get_paid_api_jobs

router = APIRouter(prefix="/jobs", tags=["paid-api-v1"])


class PaidJobItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    source: str
    source_url: str
    title: str
    company_name: str
    remote_scope: Optional[str] = None
    status: str
    remote_class: Optional[str] = None
    geo_class: Optional[str] = None
    compliance_status: Optional[str] = None
    compliance_score: Optional[int] = None
    quality_score: Optional[int] = None
    description: Optional[str] = None
    source_department: Optional[str] = None
    job_family: Optional[str] = None
    job_role: Optional[str] = None
    seniority: Optional[str] = None
    specialization: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    salary_min_eur: Optional[int] = None
    salary_max_eur: Optional[int] = None
    first_seen_at: datetime
    last_seen_at: Optional[datetime] = None


class PaginatedJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[PaidJobItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PaginatedJobsResponse)
def list_paid_jobs(
    q: Optional[str] = None,
    status: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    source: Optional[str] = None,
    remote_scope: Optional[str] = None,
    remote_class: Optional[str] = None,
    geo_class: Optional[str] = None,
    compliance_status: Optional[str] = None,
    min_compliance_score: Optional[int] = Query(None, ge=0, le=100),
    max_compliance_score: Optional[int] = Query(None, ge=0, le=100),
    job_family: Optional[str] = None,
    seniority: Optional[str] = None,
    specialization: Optional[str] = None,
    first_seen_after: Optional[date] = None,
    first_seen_before: Optional[date] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=50_000),
):
    """Return paginated jobs with full canonical fields.

    Supports all filters including taxonomy (job_family, seniority, specialization),
    compliance (compliance_status, min/max compliance_score), geo/remote classification,
    and date range (first_seen_after, first_seen_before).
    """
    items, total = get_paid_api_jobs(
        status=status,
        q=q,
        company=company,
        title=title,
        source=source,
        remote_scope=remote_scope,
        remote_class=remote_class,
        geo_class=geo_class,
        compliance_status=compliance_status,
        min_compliance_score=min_compliance_score,
        max_compliance_score=max_compliance_score,
        job_family=job_family,
        seniority=seniority,
        specialization=specialization,
        first_seen_after=first_seen_after,
        first_seen_before=first_seen_before,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
