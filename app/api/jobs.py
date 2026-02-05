from fastapi import APIRouter, Query, Response
from datetime import datetime, timezone

from storage.sqlite import get_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

FEED_LIMIT = 200
FEED_VERSION = "v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("")
def list_jobs(
    status: str | None = Query("visible"),
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
    limit: int = Query(40, ge=1, le=100),
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


def serialize_feed_job(job: dict) -> dict:
    return {
        "id": job["job_id"],
        "title": job["title"],
        "company": job["company_name"],
        "remote_scope": job["remote_scope"],
        "source": job["source"],
        "url": job["source_url"],
        "first_seen_at": job["first_seen_at"],
        "status": job["status"],
    }


@router.get("/feed")
def jobs_feed(response: Response):
    jobs = get_jobs(
        status="visible",
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
