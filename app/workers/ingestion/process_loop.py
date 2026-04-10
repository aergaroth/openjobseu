import logging
from typing import Dict, List

from sqlalchemy.engine import Connection

from app.adapters.ats.base import ATSAdapter
from app.domain.jobs.cleaning import clean_description
from app.domain.jobs.identity import compute_job_identity
from app.domain.jobs.job_processing import process_ingested_job
from app.workers.ingestion.metrics import IngestionMetrics
from storage.repositories.compliance_repository import insert_compliance_reports
from storage.repositories.jobs_repository import bulk_upsert_jobs
from storage.repositories.salary_repository import insert_salary_parsing_cases

logger = logging.getLogger("openjobseu.ingestion.employer")


def normalize_job(adapter: ATSAdapter, raw_job: dict) -> dict | None:
    return adapter.normalize(raw_job)


def process_company_jobs(
    conn: Connection,
    raw_jobs: List[Dict],
    adapter: ATSAdapter,
    company_id: str,
    provider: str,
    metrics: IngestionMetrics,
):
    """
    Process a list of raw jobs for a company: normalize, process, persist, and collect metrics.
    """
    # Collect (job, report) pairs first, then bulk-persist in one batch.
    pending: list[tuple[dict, dict]] = []

    for raw in raw_jobs:
        try:
            normalized = normalize_job(adapter, raw)
            if not normalized:
                metrics.observe_skip()
                continue

            metrics.observe_normalized()
            normalized["company_id"] = company_id

            # Clean description before fingerprint computation so the fingerprint
            # is always derived from the canonical clean text, not raw ATS HTML.
            if normalized.get("description"):
                normalized["description"] = clean_description(normalized["description"], source=provider)

            normalized = compute_job_identity(company_id, raw, normalized)

            job, report = process_ingested_job(normalized, source=provider)

            # Metrics & Logging
            compliance_payload = (job or normalized).get("_compliance", {})
            reason = report.get("policy_reason")
            remote_model = compliance_payload.get("remote_model")
            compliance_status = compliance_payload.get("compliance_status")

            metrics.observe_remote_model(remote_model)

            if not job:
                metrics.observe_skip()
                continue

            if compliance_status == "approved":
                metrics.observe_accept()
            else:
                metrics.observe_rejection(reason)

            metrics.observe_salary(bool(job.get("salary_source")))
            pending.append((job, report))

        except Exception as exc:
            logger.warning(
                "employer ingestion job processing failed",
                extra={
                    "company_id": company_id,
                    "ats_provider": provider,
                    "source_job_id": raw.get("id") if isinstance(raw, dict) else None,
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
            )
            metrics.observe_skip()
            continue

    if not pending:
        return

    # Bulk-persist all jobs in a single batch (replaces N × upsert_job calls).
    job_list = [job for job, _ in pending]
    canonical_ids = bulk_upsert_jobs(job_list, conn, company_id=company_id, source=provider)

    compliance_reports_bulk = []
    salary_cases_bulk = []

    for (job, report), canonical_job_id in zip(pending, canonical_ids):
        report["job_id"] = canonical_job_id

        parsing_case = job.get("_salary_parsing_case")
        if parsing_case and canonical_job_id:
            salary_cases_bulk.append(
                {
                    "job_id": canonical_job_id,
                    "salary_raw": parsing_case.get("salary_raw"),
                    "description_fragment": None,
                    "parser_confidence": parsing_case.get("salary_confidence"),
                    "extracted_min": parsing_case.get("salary_min"),
                    "extracted_max": parsing_case.get("salary_max"),
                    "extracted_currency": parsing_case.get("salary_currency"),
                }
            )

        if report.get("job_id"):
            compliance_reports_bulk.append(report)

    if compliance_reports_bulk:
        insert_compliance_reports(conn, compliance_reports_bulk)

    if salary_cases_bulk:
        insert_salary_parsing_cases(conn, salary_cases_bulk)
