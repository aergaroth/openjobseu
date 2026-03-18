from fastapi import APIRouter, Query

from storage.repositories.companies_repository import get_companies_paginated

router = APIRouter(prefix="/companies", tags=["companies"])

@router.get("")
def list_companies(
    q: str | None = Query(None, description="Fast fuzzy text search across legal and brand names"),
    limit: int = Query(40, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items, total = get_companies_paginated(
        q=q, limit=limit, offset=offset
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }