import logging
from typing import Dict, List

from sqlalchemy.engine import Connection

from app.adapters.ats.base import ATSAdapter
from app.domain.jobs.identity import compute_schema_hash
from app.domain.jobs.job_processing import process_ingested_job
from app.workers.ingestion.metrics import IngestionMetrics
from storage.db_logic import insert_compliance_report, upsert_job

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
    for raw in raw_jobs:
        try:
            normalized = normalize_job(adapter, raw)
            if not normalized:
                metrics.observe_skip()
                continue

            metrics.observe_normalized()
            normalized["source_schema_hash"] = compute_schema_hash(raw)
            normalized["company_id"] = company_id

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

            # Log salary detection (from worker as requested)
            salary_source = job.get("salary_source")
            if salary_source:
                logger.info(
                    f"salary_{salary_source}_detected",
                    extra={"job_id": job.get("job_id")},
                )
            else:
                logger.info("salary_missing", extra={"job_id": job.get("job_id")})

            canonical_job_id = upsert_job(job, conn=conn, company_id=company_id)
            report["job_id"] = canonical_job_id

            if report.get("job_id"):
                insert_compliance_report(
                    conn,
                    job_id=report["job_id"],
                    job_uid=report["job_uid"],
                    policy_version=report["policy_version"],
                    remote_class=report["remote_class"],
                    geo_class=report["geo_class"],
                    hard_geo_flag=report["hard_geo_flag"],
                    base_score=report["base_score"],
                    penalties=None,
                    bonuses=None,
                    final_score=report["final_score"],
                    final_status=report["final_status"],
                    decision_vector=report["decision_vector"],
                )

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