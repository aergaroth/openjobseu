import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import text

from storage.db_engine import get_engine
from app.domain.jobs.job_processing import process_ingested_job
from storage.repositories.jobs_repository import update_job_department_and_taxonomy_bulk

import app.adapters.ats as ats  # noqa: F401
from app.adapters.ats.registry import get_adapter

logger = logging.getLogger("openjobseu.backfill")


def _fetch_and_process_company(company: dict) -> list[dict]:
    """
    Fetches and processes jobs for a single company, returning a list of updates.
    """
    # Provider must come from company_ats.provider.
    provider = company.get("provider")
    company_name = company.get("legal_name") or company.get("name") or company.get("company_id")

    if not provider:
        logger.warning(
            "backfill_department_skipped_missing_provider",
            extra={"company_id": company.get("company_id")},
        )
        return []

    logger.info(f"Fetching jobs for {company_name} ({provider})...")

    try:
        adapter = get_adapter(provider)
        # Force full fetch without time filter (updated_since=None)
        raw_jobs = adapter.fetch(company, updated_since=None)
    except Exception:
        logger.warning(
            "backfill_department_failed_fetch",
            extra={"company_id": company.get("company_id")},
            exc_info=True,
        )
        return []

    updates_for_company = []
    for raw_job in raw_jobs:
        normalized = adapter.normalize(raw_job)
        if not normalized or not normalized.get("department"):
            continue

        # Pass the job through taxonomy classifier
        processed, _ = process_ingested_job(normalized, source=provider)
        if not processed:
            processed = normalized

        # Prepare the dictionary for the bulk update
        update_params = {
            "source": processed.get("source"),
            "source_job_id": processed.get("source_job_id"),
            "source_department": str(normalized["department"])[:255],
            "job_family": processed.get("job_family"),
            "job_role": processed.get("job_role"),
            "seniority": processed.get("seniority"),
            "specialization": processed.get("specialization"),
        }
        updates_for_company.append(update_params)

    return updates_for_company


def backfill_missing_departments() -> int:
    """
    Refetches data from API for active companies concurrently and updates
    source_department and taxonomy for jobs that don't have this field populated yet
    in a single bulk operation.

    Only fetches from companies that actually have jobs with missing source_department —
    avoids scanning all 100+ companies when backfill is complete or nearly complete.
    """
    engine = get_engine()

    with engine.connect() as conn:
        rows = (
            conn.execute(
                text("""
                SELECT DISTINCT
                    ca.company_ats_id,
                    ca.company_id,
                    c.legal_name,
                    ca.provider,
                    ca.provider AS ats_provider,
                    ca.ats_slug,
                    ca.ats_api_url,
                    ca.careers_url,
                    ca.last_sync_at
                FROM jobs j
                JOIN company_ats ca ON ca.company_id = j.company_id
                JOIN companies c ON c.company_id = ca.company_id
                WHERE j.source_department IS NULL
                  AND c.is_active = TRUE
                  AND ca.is_active = TRUE
                  AND ca.provider IS NOT NULL
                  AND ca.ats_slug IS NOT NULL
            """)
            )
            .mappings()
            .all()
        )
        companies = [dict(r) for r in rows]

    if not companies:
        logger.info("backfill_department_skipped: no companies with jobs missing source_department")
        return 0

    all_updates = []
    total_companies = len(companies)
    logger.info(f"Found {total_companies} active companies to process.")

    # Using ThreadPoolExecutor to fetch in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_company = {executor.submit(_fetch_and_process_company, dict(c)): c for c in companies}

        for i, future in enumerate(as_completed(future_to_company), 1):
            company_row = future_to_company[future]
            company_name = company_row.get("legal_name") or company_row.get("name") or company_row.get("company_id")
            try:
                company_updates = future.result()
                if company_updates:
                    all_updates.extend(company_updates)
                logger.info(
                    f"({i}/{total_companies}) Finished processing {company_name}, found {len(company_updates)} updates."
                )
            except Exception:
                logger.error(f"Error processing future for {company_name}", exc_info=True)

    if not all_updates:
        logger.info("No department updates to perform.")
        return 0

    logger.info(f"Collected a total of {len(all_updates)} job updates. Applying to database...")

    updated_count = 0
    try:
        with engine.begin() as conn:
            updated_count = update_job_department_and_taxonomy_bulk(conn, all_updates)
    except Exception:
        logger.error("Failed to perform bulk update for department backfill", exc_info=True)

    logger.info("backfill_department_completed", extra={"updated_count": updated_count})
    return updated_count
