from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Query, Response

from storage.repositories.companies_repository import get_companies_paginated

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_id: str
    legal_name: str
    brand_name: str
    hq_country: Optional[str] = None
    remote_posture: str
    approved_jobs_count: int
    total_jobs_count: int


class PaginatedCompaniesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: List[CompanyItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=PaginatedCompaniesResponse)
def list_companies(
    response: Response,
    q: str | None = Query(None, description="Fast fuzzy text search across legal and brand names"),
    limit: int = Query(40, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000, description="Pagination offset (max 10000)"),
):
    response.headers["Cache-Control"] = "public, max-age=60"
    items, total = get_companies_paginated(q=q, limit=limit, offset=offset)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
