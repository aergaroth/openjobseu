from fastapi import APIRouter, Query
from storage.sqlite import get_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("")
def list_jobs(
    status: str | None = Query("visible"),
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return {
        "items": get_jobs(
            status=status,
            company=company,
            title=title,
            source=source,
            remote_scope=remote_scope,
            limit=limit,
            offset=offset,
        )
    }
