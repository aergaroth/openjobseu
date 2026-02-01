from fastapi import APIRouter, Query
from storage.sqlite import get_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    jobs = get_jobs(status=status, limit=limit, offset=offset)

    return {
        "count": len(jobs),
        "items": jobs,
    }
