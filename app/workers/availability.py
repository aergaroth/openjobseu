from datetime import datetime, timezone
import logging
import requests

logger = logging.getLogger("openjobseu.worker.availability")
from storage.sqlite import get_jobs_for_verification, update_job_availability


DEFAULT_TIMEOUT = 5


def check_job_availability(job: dict, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Check availability of a single job offer.

    Returns one of: active | expired | unreachable
    """
    url = job.get("source_url")

    if not url:
        logger.warning("job missing source_url", extra={"job_id": job.get("job_id")})
        return "unreachable"

    try:
        resp = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
        )

        status = resp.status_code

        if status in (404, 410):
            return "expired"

        if status >= 500:
            return "unreachable"

        return "active"

    except requests.RequestException as exc:
        logger.warning(
            "availability check failed",
            extra={
                "job_id": job.get("job_id"),
                "error": str(exc),
            },
        )
        return "unreachable"


def run_availability_checks(jobs: list[dict]) -> dict:
    """
    Run availability checks for a batch of jobs.
    Returns summary statistics.
    """
    summary = {
        "checked": 0,
        "active": 0,
        "expired": 0,
        "unreachable": 0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    for job in jobs:
        status = check_job_availability(job)

        summary["checked"] += 1
        summary[status] += 1

        job["availability_status"] = status  # transient, DB update elsewhere

    logger.info("availability checks completed", extra=summary)
    return summary



from storage.sqlite import (
    get_jobs_for_verification,
    update_job_availability,
)


def run_availability_pipeline() -> None:
    """
    Pipeline-level availability stage.
    Fetches jobs, checks availability and persists results.
    """

    jobs = get_jobs_for_verification(limit=20)
    now = datetime.now(timezone.utc).isoformat()

    for job in jobs:
        status = check_job_availability(job)

        update_job_availability(
            job_id=job["job_id"],
            status=status,
            verified_at=now,
            failure=(status == "unreachable"),
        )

    logger.info(
        "availability pipeline completed",
        extra={"checked": len(jobs)},
    )
