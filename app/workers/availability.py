from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime, timezone
import logging
import requests
import os
import time
from storage.db_engine import get_engine
from storage.repositories.availability_repository import (
    get_jobs_for_verification,
    update_jobs_availability,
)
from app.adapters.ats.base import TimeoutSession

logger = logging.getLogger("openjobseu.worker.availability")


DEFAULT_TIMEOUT = 5
MAX_AVAILABILITY_WORKERS = 8

# Inicjalizujemy globalną sesję (współdzieloną w ramach thread poola) z mechanizmem retry i timeout
_session = TimeoutSession(timeout=DEFAULT_TIMEOUT)


def check_job_availability(job: dict, timeout: int = DEFAULT_TIMEOUT, session: requests.Session = _session) -> str:
    """
    Check availability of a single job offer.

    Returns one of: active | expired | unreachable
    """
    url = job.get("source_url")

    if not url:
        return "unreachable"

    start_time = time.perf_counter()

    try:
        resp = session.head(
            url,
            timeout=timeout,
            allow_redirects=True,
        )

        status = resp.status_code

        if status in (404, 410):
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "job availability expired",
                extra={
                    "job_id": job.get("job_id"),
                    "url": url,
                    "status_code": status,
                    "duration_ms": duration_ms,
                },
            )
            return "expired"

        if status >= 500:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "job availability returned server error",
                extra={
                    "job_id": job.get("job_id"),
                    "url": url,
                    "status_code": status,
                    "duration_ms": duration_ms,
                },
            )
            return "unreachable"

        return "active"

    except requests.RequestException as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(
            "job availability check failed",
            extra={
                "job_id": job.get("job_id"),
                "url": url,
                "error_type": type(exc).__name__,
                "duration_ms": duration_ms,
            },
        )
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

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {executor.submit(check_job_availability, job): index for index, job in enumerate(jobs)}

        try:
            for future in as_completed(future_to_index, timeout=60):
                try:
                    statuses[future_to_index[future]] = future.result()
                except Exception:
                    pass
        except TimeoutError:
            logger.error(
                "availability_pool_timeout",
                extra={
                    "details": "Thread pool exhausted on hanging requests",
                    "timeout_sec": 60,
                },
            )
            for f in future_to_index:
                f.cancel()

    return statuses


def run_availability_checks(jobs: list[dict]) -> dict:
    """
    Run availability checks for a batch of jobs.
    Returns summary statistics.
    """
    start_time = time.perf_counter()
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

    summary["duration_ms"] = int((time.perf_counter() - start_time) * 1000)
    logger.info("availability checks completed", extra=summary)
    return summary


def run_availability_pipeline() -> dict:
    """
    Pipeline-level availability stage.
    Fetches jobs, checks availability and persists results.
    """
    # init_db()  # initialized at app startup in app/main.py

    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)

    # Adaptacyjny time-budget: upewniamy się, że nie przekroczymy timeoutu Cloud Run (np. 30s).
    # Domyślnie przeznaczamy max 15 sekund na odpytywanie serwerów dla tego konkretnego workera.
    max_execution_time = float(os.environ.get("AVAILABILITY_TIME_BUDGET_SEC", 15.0))
    chunk_size = int(os.environ.get("AVAILABILITY_CHUNK_SIZE", 50))

    summary = {
        "checked": 0,
        "active": 0,
        "expired": 0,
        "unreachable": 0,
    }

    db_engine = get_engine()

    while time.perf_counter() - start_time < max_execution_time:
        jobs = get_jobs_for_verification(limit=chunk_size)
        if not jobs:
            break  # Brak ofert wymagających weryfikacji w bazie

        statuses = _check_availability_for_jobs(jobs)
        updates: list[dict] = []
        for job, status in zip(jobs, statuses):
            summary["checked"] += 1
            summary[status] += 1

            updates.append(
                {
                    "job_id": job["job_id"],
                    "availability_status": status,
                    "verified_at": now,
                    "failure": status == "unreachable",
                    "updated_at": now,
                }
            )

        if updates:
            with db_engine.begin() as conn:
                # Zapis zaktualizuje "last_verified_at",
                # więc to zapobiegnie pobraniu tych samych ofert w następnej pętli
                update_jobs_availability(updates=updates, conn=conn)

        if len(jobs) < chunk_size:
            break  # Pobraliśmy mniej niż limit, kolejka jest pusta

    summary["status"] = "ok"
    summary["duration_ms"] = int((time.perf_counter() - start_time) * 1000)
    return {"metrics": summary}
