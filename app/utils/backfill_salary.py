from datetime import datetime, timezone
import logging

from app.domain.money.salary_parser import extract_salary
from storage.db_engine import get_engine
from storage.repositories.salary_repository import (
    get_jobs_with_missing_salary,
    update_job_salaries_bulk,
)

logger = logging.getLogger("openjobseu.backfill")

BATCH_SIZE = 100


def backfill_missing_salary_fields(limit: int = 1000) -> int:
    """
    Backfill missing salary fields by re-parsing description and title.
    Only updates rows where BOTH salary_min AND salary_max are NULL.
    """
    engine = get_engine()

    logger.info("Starting salary backfill...")

    rows = []
    with engine.connect() as conn:
        rows = get_jobs_with_missing_salary(conn, limit)

    total_found = len(rows)
    logger.info(f"Found {total_found} jobs with missing salary to backfill")

    if total_found == 0:
        return 0

    processed = 0
    updated = 0

    for i in range(0, total_found, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        job_updates = []

        for row in batch:
            job_id = row["job_id"]
            title = row["title"] or ""
            description = row["description"] or ""

            try:
                salary_info = extract_salary(description, title=title)

                if salary_info and (
                    salary_info.get("salary_min") is not None or salary_info.get("salary_max") is not None
                ):
                    job_updates.append(
                        {
                            "job_id": job_id,
                            "salary_min": int(salary_info["salary_min"])
                            if salary_info.get("salary_min") is not None
                            else None,
                            "salary_max": int(salary_info["salary_max"])
                            if salary_info.get("salary_max") is not None
                            else None,
                            "salary_currency": salary_info.get("salary_currency"),
                            "salary_period": salary_info.get("salary_period"),
                            "salary_source": salary_info.get("salary_source"),
                            "salary_min_eur": int(salary_info["salary_min_eur"])
                            if salary_info.get("salary_min_eur") is not None
                            else None,
                            "salary_max_eur": int(salary_info["salary_max_eur"])
                            if salary_info.get("salary_max_eur") is not None
                            else None,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    )
            except Exception:
                logger.error(f"Failed to extract salary for job {job_id}", exc_info=True)
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    update_job_salaries_bulk(conn, job_updates)
                updated += len(job_updates)
            except Exception:
                failed_ids = [j["job_id"] for j in job_updates]
                logger.warning("Failed to update salary batch. Job IDs: %s", failed_ids)
                logger.error("Salary batch update failed", exc_info=True)

        processed += len(batch)
        pct = int((processed / total_found) * 100)
        filled = int(20 * processed / total_found)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(f"salary_backfill progress: [{bar}] {pct}% ({processed}/{total_found}) | updated: {updated}")

    logger.info(f"Salary backfill finished. Total jobs updated: {updated}")
    return updated
