import logging
from sqlalchemy import text

from storage.db_engine import get_engine
from storage.repositories.ats_repository import load_active_ats_companies
from app.domain.jobs.job_processing import process_ingested_job

from app.adapters.ats.greenhouse import GreenhouseAdapter
from app.adapters.ats.lever import LeverAdapter
from app.adapters.ats.workable import WorkableAdapter
from app.adapters.ats.ashby import AshbyAdapter

logger = logging.getLogger("openjobseu.backfill")

ADAPTER_MAP = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "workable": WorkableAdapter,
    "ashby": AshbyAdapter,
}


def backfill_missing_departments() -> int:
    """
    Refetches data from API for active companies and updates source_department
    and taxonomy for jobs that don't have this field populated yet.
    """
    engine = get_engine()
    updated_count = 0

    with engine.connect() as conn:
        companies = load_active_ats_companies(conn, limit=10000)

    for row in companies:
        company = dict(row)
        provider = company.get("provider")
        adapter_cls = ADAPTER_MAP.get(provider)
        
        if not adapter_cls:
            continue

        adapter = adapter_cls()

        try:
            # Force full fetch without time filter (updated_since=None)
            raw_jobs = adapter.fetch(company, updated_since=None)
            
            for raw_job in raw_jobs:
                normalized = adapter.normalize(raw_job)
                if not normalized or not normalized.get("department"):
                    continue

                # Pass the job through taxonomy classifier (will detect job_family from department, etc.)
                processed, _ = process_ingested_job(normalized, source=provider)
                if not processed:
                    processed = normalized

                with engine.begin() as update_conn:
                    result = update_conn.execute(
                        text("""
                            UPDATE jobs 
                            SET source_department = :source_department,
                                job_family = :job_family,
                                job_role = :job_role,
                                seniority = :seniority,
                                specialization = :specialization
                            WHERE source = :source AND source_job_id = :source_job_id
                              AND source_department IS NULL
                        """),
                        {
                            "source_department": str(normalized["department"])[:255],
                            "job_family": processed.get("job_family"),
                            "job_role": processed.get("job_role"),
                            "seniority": processed.get("seniority"),
                            "specialization": processed.get("specialization"),
                            "source": processed.get("source"),
                            "source_job_id": processed.get("source_job_id"),
                        }
                    )
                    updated_count += result.rowcount

        except Exception as e:
            logger.warning("backfill_department_failed", extra={"company_id": company.get("company_id"), "error": str(e)})

    logger.info("backfill_department_completed", extra={"updated_count": updated_count})
    return updated_count