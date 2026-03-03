from datetime import datetime, timezone
import logging
from time import perf_counter

import requests
from sqlalchemy import text

from app.domain.classification.enums import RemoteClass
from storage.db_engine import get_engine
from storage.db_logic import upsert_job

from ingestion.adapters.greenhouse_api import GreenhouseApiAdapter
from app.workers.ingestion.log_helpers import log_ingestion
from app.workers.normalization.greenhouse import normalize_greenhouse_job
from app.workers.policy.v3.apply_policy_v3 import apply_policy_v3

logger = logging.getLogger("openjobseu.ingestion.employer")
SOURCE = "employer_ing"


def _normalize_remote_model_for_metrics(remote_model: str | None) -> str:
    model = (remote_model or "").strip().lower()
    if model == RemoteClass.REMOTE_ONLY.value:
        return RemoteClass.REMOTE_ONLY.value
    if model in {RemoteClass.REMOTE_REGION_LOCKED.value, "remote_but_geo_restricted"}:
        return "remote_but_geo_restricted"
    if model in {"office_first", "hybrid"}:
        return RemoteClass.NON_REMOTE.value
    return RemoteClass.UNKNOWN.value


def load_active_ats_companies(conn):
    rows = conn.execute(
        text("""
            SELECT
                company_id,
                legal_name,
                ats_provider,
                ats_slug
            FROM companies
            WHERE is_active = TRUE
              AND ats_provider IS NOT NULL
              AND ats_slug IS NOT NULL
        """)
    ).mappings().all()

    return [dict(row) for row in rows]


def ingest_company(company: dict):

    provider = str(company.get("ats_provider") or "").strip().lower()

    if provider != "greenhouse":
        logger.warning(
            "employer ingestion skipped due to unsupported ats provider",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": company.get("ats_provider"),
                "ats_slug": company.get("ats_slug"),
            },
        )
        return {
            "fetched": 0,
            "normalized_count": 0,
            "accepted": 0,
            "skipped": 0,
            "error": "unsupported_ats_provider",
        }

    try:
        adapter = GreenhouseApiAdapter(company["ats_slug"])
        raw_jobs = adapter.fetch()
    except requests.HTTPError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "employer ingestion fetch failed with http status",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "status_code": status_code,
            },
        )
        return {
            "fetched": 0,
            "normalized_count": 0,
            "accepted": 0,
            "skipped": 0,
            "error": "invalid_ats_slug" if status_code == 404 else "fetch_failed",
        }
    except (requests.ConnectionError, requests.Timeout) as exc:
        logger.warning(
            "employer ingestion fetch failed due to network error",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
            },
        )
        return {
            "fetched": 0,
            "normalized_count": 0,
            "accepted": 0,
            "skipped": 0,
            "error": "fetch_network_failed",
        }
    except requests.RequestException as exc:
        logger.warning(
            "employer ingestion fetch failed due to request exception",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
            },
        )
        return {
            "fetched": 0,
            "normalized_count": 0,
            "accepted": 0,
            "skipped": 0,
            "error": "fetch_failed",
        }
    except Exception:
        return {
            "fetched": 0,
            "normalized_count": 0,
            "accepted": 0,
            "skipped": 0,
            "error": "fetch_failed",
        }

    engine = get_engine()
    normalized_count = 0
    accepted = 0
    skipped = 0
    rejected_policy_count = 0
    hard_geo_rejected_count = 0
    rejected_by_reason = {
        RemoteClass.NON_REMOTE.value: 0,
        "geo_restriction": 0,
    }
    remote_model_counts = {
        RemoteClass.REMOTE_ONLY.value: 0,
        "remote_but_geo_restricted": 0,
        RemoteClass.NON_REMOTE.value: 0,
        RemoteClass.UNKNOWN.value: 0,
    }

    try:
        with engine.begin() as conn:
            for raw in raw_jobs:
                try:
                    normalized = normalize_greenhouse_job(
                        raw, adapter.board_token
                    )
                    if not normalized:
                        skipped += 1
                        continue
                    normalized_count += 1

                    job, reason = apply_policy_v3(
                        normalized,
                        source=f"greenhouse:{adapter.board_token}",
                    )

                    metric_remote_model = _normalize_remote_model_for_metrics(
                        (job or normalized).get("_compliance", {}).get("remote_model")
                    )
                    remote_model_counts[metric_remote_model] += 1

                    if reason == "geo_restriction_hard":
                        rejected_policy_count += 1
                        rejected_by_reason["geo_restriction"] += 1
                        hard_geo_rejected_count += 1
                        skipped += 1
                        continue

                    if reason in rejected_by_reason:
                        rejected_policy_count += 1
                        rejected_by_reason[reason] += 1

                    if not job:
                        skipped += 1
                        continue

                    compliance_status = job.get("compliance_status")
                    if compliance_status and compliance_status != "approved":
                        skipped += 1
                        continue

                    upsert_job(
                        job,
                        conn=conn,
                        company_id=company["company_id"],
                    )

                    accepted += 1

                except Exception:
                    skipped += 1
                    continue

    except Exception:
        return {
            "fetched": len(raw_jobs),
            "normalized_count": normalized_count,
            "accepted": 0,
            "skipped": 0,
            "error": "transaction_failed",
        }

    return {
        "fetched": len(raw_jobs),
        "normalized_count": normalized_count,
        "accepted": accepted,
        "skipped": skipped,
        "rejected_policy_count": rejected_policy_count,
        "rejected_by_reason": rejected_by_reason,
        "remote_model_counts": remote_model_counts,
        "hard_geo_rejected_count": hard_geo_rejected_count,
    }


def run_employer_ingestion() -> dict:

    started = perf_counter()
    engine = get_engine()
    companies_load_duration_ms = 0
    ingestion_loop_duration_ms = 0

    total_companies = 0
    companies_failed = 0
    companies_invalid_slug = 0
    total_fetched = 0
    total_normalized = 0
    total_skipped = 0
    total_accepted = 0
    total_rejected_policy = 0
    rejected_by_reason = {
        RemoteClass.NON_REMOTE.value: 0,
        "geo_restriction": 0,
    }
    remote_model_counts = {
        RemoteClass.REMOTE_ONLY.value: 0,
        "remote_but_geo_restricted": 0,
        RemoteClass.NON_REMOTE.value: 0,
        RemoteClass.UNKNOWN.value: 0,
    }
    total_hard_geo_rejected = 0

    try:
        companies_load_started = perf_counter()
        with engine.connect() as conn:
            companies = load_active_ats_companies(conn)
        companies_load_duration_ms = int((perf_counter() - companies_load_started) * 1000)

        total_companies = len(companies)
        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=total_companies,
            companies_processed=total_companies,
            companies_load_duration_ms=companies_load_duration_ms,
        )

        ingestion_loop_started = perf_counter()
        for company in companies:
            try:
                result = ingest_company(company)

                if "error" in result:
                    companies_failed += 1
                    if result.get("error") == "invalid_ats_slug":
                        companies_invalid_slug += 1
                    continue

                total_fetched += int(result.get("fetched", 0) or 0)
                total_normalized += int(result.get("normalized_count", 0) or 0)
                total_accepted += result["accepted"]
                total_skipped += int(result.get("skipped", 0) or 0)
                total_rejected_policy += int(result.get("rejected_policy_count", 0) or 0)
                source_reasons = result.get("rejected_by_reason", {}) or {}
                rejected_by_reason[RemoteClass.NON_REMOTE.value] += int(
                    source_reasons.get(RemoteClass.NON_REMOTE.value, 0) or 0
                )
                rejected_by_reason["geo_restriction"] += int(source_reasons.get("geo_restriction", 0) or 0)
                source_remote_model = result.get("remote_model_counts", {}) or {}
                for key in remote_model_counts:
                    remote_model_counts[key] += int(source_remote_model.get(key, 0) or 0)
                total_hard_geo_rejected += int(result.get("hard_geo_rejected_count", 0) or 0)

            except Exception:
                companies_failed += 1
                continue
        ingestion_loop_duration_ms = int((perf_counter() - ingestion_loop_started) * 1000)

    except Exception as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        log_ingestion(
            source=SOURCE,
            phase="error",
            raw_count=total_fetched,
            normalized=total_normalized,
            persisted=total_accepted,
            skipped=total_skipped,
            rejected_policy=total_rejected_policy,
            rejected_non_remote=rejected_by_reason[RemoteClass.NON_REMOTE.value],
            rejected_geo_restriction=rejected_by_reason["geo_restriction"],
            remote_model_counts=remote_model_counts.copy(),
            companies_processed=total_companies,
            companies_failed=companies_failed,
            companies_invalid_slug=companies_invalid_slug,
            hard_geo_rejected_count=total_hard_geo_rejected,
            companies_load_duration_ms=companies_load_duration_ms,
            ingestion_loop_duration_ms=ingestion_loop_duration_ms,
            duration_ms=duration_ms,
            error=str(exc),
        )
        raise

    duration_ms = int((perf_counter() - started) * 1000)
    log_ingestion(
        source=SOURCE,
        phase="ingestion_summary",
        fetched=total_fetched,
        normalized=total_normalized,
        accepted=total_accepted,
        rejected_policy=total_rejected_policy,
        rejected_non_remote=rejected_by_reason[RemoteClass.NON_REMOTE.value],
        rejected_geo_restriction=rejected_by_reason["geo_restriction"],
        remote_model_counts=remote_model_counts.copy(),
        companies_processed=total_companies,
        companies_failed=companies_failed,
        companies_invalid_slug=companies_invalid_slug,
        hard_geo_rejected_count=total_hard_geo_rejected,
        companies_load_duration_ms=companies_load_duration_ms,
        ingestion_loop_duration_ms=ingestion_loop_duration_ms,
        duration_ms=duration_ms,
    )

    return {
        "actions": ["employer_ingestion_completed"],
        "metrics": {
            "source": SOURCE,
            "status": "ok",
            "fetched_count": total_fetched,
            "normalized_count": total_normalized,
            "accepted_count": total_accepted,
            "raw_count": total_fetched,
            "persisted_count": total_accepted,
            "skipped_count": total_skipped,
            "rejected_policy_count": total_rejected_policy,
            "policy_rejected_total": total_rejected_policy,
            "policy_rejected_by_reason": rejected_by_reason.copy(),
            "remote_model_counts": remote_model_counts.copy(),
            "companies_processed": total_companies,
            "companies_failed": companies_failed,
            "companies_invalid_slug": companies_invalid_slug,
            "accepted_jobs": total_accepted,
            "hard_geo_rejected_count": total_hard_geo_rejected,
            "duration_ms": duration_ms,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
