from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import logging
import requests
from storage.db import get_engine
from storage.sqlite import get_jobs_for_verification, update_jobs_availability

logger = logging.getLogger("openjobseu.worker.availability")


DEFAULT_TIMEOUT = 5
MAX_AVAILABILITY_WORKERS = 8


def check_job_availability(job: dict, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Check availability of a single job offer.

    Returns one of: active | expired | unreachable
    """
    url = job.get("source_url")

    if not url:
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

    except requests.RequestException:
        return "unreachable"


def _check_availability_for_jobs(
    jobs: list[dict],
) -> list[str]:
    if not jobs:
        return []

    if len(jobs) == 1:
        return [check_job_availability(jobs[0])]

    statuses: list[str] = ["unreachable"] * len(jobs)
    workers = min(MAX_AVAILABILITY_WORKERS, len(jobs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_index = {
            pool.submit(check_job_availability, job): index
            for index, job in enumerate(jobs)
        }
        for future in as_completed(future_to_index):
            statuses[future_to_index[future]] = future.result()

    return statuses


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

    statuses = _check_availability_for_jobs(jobs)
    for job, status in zip(jobs, statuses):

        summary["checked"] += 1
        summary[status] += 1

        job["availability_status"] = status  # transient, DB update elsewhere

    logger.info("availability checks completed", extra=summary)
    return summary

def run_availability_pipeline() -> dict:
    """
    Pipeline-level availability stage.
    Fetches jobs, checks availability and persists results.
    """
    # init_db()  # initialized at app startup in app/main.py

    jobs = get_jobs_for_verification(limit=20)
    now = datetime.now(timezone.utc)

    summary = {
        "checked": 0,
        "active": 0,
        "expired": 0,
        "unreachable": 0,
    }
    statuses = _check_availability_for_jobs(jobs)
    updates: list[dict] = []
    for job, status in zip(jobs, statuses):
        summary["checked"] += 1
        summary[status] += 1

        updates.append(
            {
                "job_id": job["job_id"],
                "status": status,
                "verified_at": now,
                "failure": status == "unreachable",
                "updated_at": now,
            }
        )

    if updates:
        db_engine = get_engine()
        with db_engine.begin() as conn:
            update_jobs_availability(updates=updates, conn=conn)

    return summary
