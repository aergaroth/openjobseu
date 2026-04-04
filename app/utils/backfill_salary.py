from datetime import datetime, timezone
import logging

from app.domain.money.salary_parser import extract_salary
from storage.db_engine import get_engine
from storage.repositories.salary_repository import (
    get_jobs_with_missing_salary,
    update_job_salaries_bulk,
)

logger = logging.getLogger("openjobseu.backfill")

# Records fetched, processed, and committed in one atomic unit.
CHUNK_SIZE = 100


def backfill_missing_salary_fields(limit: int = 1000) -> dict:
    """
    Backfill missing salary fields by re-parsing description and title.
    Only updates rows where BOTH salary_min AND salary_max are NULL.

    Processes records in chunks of CHUNK_SIZE: each iteration fetches a fresh
    batch from the DB, parses salaries, and commits atomically.

    Returns {"processed": int, "updated": int}.
    Callers should continue only if processed >= limit AND updated > 0.
    If updated == 0, all fetched records had no parseable salary — re-running
    would fetch the same records again (infinite loop).
    """
    engine = get_engine()

    logger.info("Starting salary backfill (limit=%d, chunk_size=%d)", limit, CHUNK_SIZE)

    total_processed = 0
    total_updated = 0

    while total_processed < limit:
        chunk_size = min(CHUNK_SIZE, limit - total_processed)

        # Fresh fetch per chunk — salary_min/max may have been filled by a concurrent task.
        with engine.connect() as conn:
            rows = get_jobs_with_missing_salary(conn, chunk_size)

        if not rows:
            break

        job_updates = []

        for row in rows:
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
                logger.error("Failed to extract salary for job %s", job_id, exc_info=True)
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    update_job_salaries_bulk(conn, job_updates)
                total_updated += len(job_updates)
            except Exception:
                failed_ids = [j["job_id"] for j in job_updates]
                logger.error("Salary chunk update failed. Job IDs: %s", failed_ids, exc_info=True)

        fetched = len(rows)
        total_processed += fetched

        filled = int(20 * total_processed / limit)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(
            "salary_backfill progress: [%s] %d%% (%d/%d) | updated: %d",
            bar,
            int(total_processed / limit * 100),
            total_processed,
            limit,
            total_updated,
        )

        if fetched < chunk_size:
            break  # No more records available — done early

    logger.info("Salary backfill finished. processed=%d updated=%d", total_processed, total_updated)
    return {"processed": total_processed, "updated": total_updated}
