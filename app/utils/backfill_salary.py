from datetime import datetime, timezone
import logging
from sqlalchemy import text
from app.domain.money.salary_parser import extract_salary
from storage.db_engine import get_engine

logger = logging.getLogger("openjobseu.backfill")

BATCH_SIZE = 100

def backfill_missing_salary_fields(limit: int = 1000) -> int:
    """
    Backfill missing salary fields by re-parsing description and title.
    Only updates rows where BOTH salary_min AND salary_max are NULL.
    """
    engine = get_engine()

    logger.info("Starting salary backfill...")

    query = text("""
        SELECT
            job_id, title, description
        FROM jobs
        WHERE salary_min IS NULL AND salary_max IS NULL
        ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
        LIMIT :limit
    """)

    rows = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit}).mappings().all()

    total_found = len(rows)
    logger.info(f"Found {total_found} jobs with missing salary to backfill")

    if total_found == 0:
        return 0

    processed = 0
    updated = 0

    for i in range(0, total_found, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        job_updates = []

        for row in batch:
            job_id = row["job_id"]
            title = row["title"] or ""
            description = row["description"] or ""

            try:
                salary_info = extract_salary(description, title=title)
                
                if salary_info and (salary_info.get("salary_min") is not None or salary_info.get("salary_max") is not None):
                    job_updates.append({
                        "job_id": job_id,
                        "salary_min": int(salary_info["salary_min"]) if salary_info.get("salary_min") is not None else None,
                        "salary_max": int(salary_info["salary_max"]) if salary_info.get("salary_max") is not None else None,
                        "salary_currency": salary_info.get("salary_currency"),
                        "salary_period": salary_info.get("salary_period"),
                        "salary_source": salary_info.get("salary_source"),
                        "salary_min_eur": int(salary_info["salary_min_eur"]) if salary_info.get("salary_min_eur") is not None else None,
                        "salary_max_eur": int(salary_info["salary_max_eur"]) if salary_info.get("salary_max_eur") is not None else None,
                        "updated_at": datetime.now(timezone.utc)
                    })
            except Exception as e:
                logger.error(f"Failed to extract salary for job {job_id}: {e}")
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE jobs
                            SET
                                salary_min = :salary_min,
                                salary_max = :salary_max,
                                salary_currency = :salary_currency,
                                salary_period = :salary_period,
                                salary_source = :salary_source,
                                salary_min_eur = :salary_min_eur,
                                salary_max_eur = :salary_max_eur,
                                updated_at = :updated_at
                            WHERE job_id = :job_id
                        """),
                        job_updates
                    )
                updated += len(job_updates)
            except Exception as e:
                logger.error(f"Failed to update salary batch: {e}")

        processed += len(batch)
        pct = int((processed / total_found) * 100)
        filled = int(20 * processed / total_found)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(f"salary_backfill progress: [{bar}] {pct}% ({processed}/{total_found}) | updated: {updated}")

    logger.info(f"Salary backfill finished. Total jobs updated: {updated}")
    return updated
