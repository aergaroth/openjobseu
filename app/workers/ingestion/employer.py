from datetime import datetime, timezone
import logging
from time import perf_counter
import concurrent.futures
from typing import Iterator

import app.adapters.ats as ats  # noqa: F401
from app.adapters.ats.registry import get_adapter
from app.domain.jobs.enums import RemoteClass

from storage.db_engine import get_engine
from storage.repositories.ats_repository import (
    load_active_ats_companies,
    mark_ats_synced,
)

from app.utils.tick_context import get_current_tick_context
from app.workers.ingestion.log_helpers import log_ingestion
from app.workers.ingestion.fetch import FetchCompanyJobsError, fetch_company_jobs
from app.workers.ingestion.metrics import IngestionMetrics
from app.workers.ingestion.process_loop import process_company_jobs

logger = logging.getLogger("openjobseu.ingestion.employer")
SOURCE = "employer_ing"

GLOBAL_INCREMENTAL_FETCH = True
GLOBAL_COMPANIES_LIMIT = 100
INGESTION_POOL_TIMEOUT_SECONDS = 1740


def _merge_metrics(target: IngestionMetrics, source: IngestionMetrics):
    target.normalized += source.normalized
    target.accepted += source.accepted
    target.skipped += source.skipped
    target.rejected_policy_count += source.rejected_policy_count
    target.hard_geo_rejected_count += source.hard_geo_rejected_count
    target.salary_detected += source.salary_detected
    target.salary_missing += source.salary_missing

    for reason, count in source.rejected_by_reason.items():
        target.rejected_by_reason[reason] += count

    for remote_model, count in source.remote_model_counts.items():
        target.remote_model_counts[remote_model] += count


def _iter_job_batches(
    raw_jobs: Iterator[dict],
    batch_size: int,
):
    while True:
        batch = []
        fetch_error = None
        completed = False

        try:
            for _ in range(batch_size):
                batch.append(next(raw_jobs))
        except StopIteration:
            completed = True
        except FetchCompanyJobsError as exc:
            fetch_error = exc

        if batch or fetch_error:
            yield batch, fetch_error

        if fetch_error:
            break

        if completed:
            break


def ingest_company(company: dict):
    started = perf_counter()
    provider = str(company.get("ats_provider") or "").strip().lower()
    updated_since = company.get("last_sync_at") if GLOBAL_INCREMENTAL_FETCH else None
    company_id = str(company.get("company_id") or "")
    ats_slug = company.get("ats_slug")
    tick_context = get_current_tick_context()

    logger.info(
        "company_ingestion_start",
        extra={
            "company_id": company_id,
            "ats_provider": provider,
            "ats_slug": ats_slug,
            **tick_context,
        },
    )

    def _finalize(res: dict) -> dict:
        duration_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "company_ingestion_summary",
            extra={
                "company_id": company_id,
                "ats_provider": provider,
                "ats_slug": ats_slug,
                "duration_ms": duration_ms,
                "fetched": res.get("fetched", 0),
                "accepted": res.get("accepted", 0),
                "skipped": res.get("skipped", 0),
                "error": res.get("error"),
                "salary_detected": res.get("salary_detected", 0),
                **tick_context,
            },
        )
        return res

    try:
        adapter = get_adapter(provider)
    except ValueError:
        logger.warning(
            "employer ingestion skipped due to unsupported ats provider",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": company.get("ats_provider"),
                "ats_slug": company.get("ats_slug"),
                **tick_context,
            },
        )
        return _finalize(
            {
                "fetched": 0,
                "normalized_count": 0,
                "accepted": 0,
                "skipped": 0,
                "error": "unsupported_ats_provider",
            }
        )

    if not getattr(adapter, "active", True):
        logger.warning(
            "employer ingestion skipped due to inactive ats adapter",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                **tick_context,
            },
        )
        return _finalize(
            {
                "fetched": 0,
                "normalized_count": 0,
                "accepted": 0,
                "skipped": 0,
                "error": "inactive_ats_adapter",
            }
        )

    raw_jobs, error = fetch_company_jobs(company, adapter, updated_since=updated_since)
    if error:
        engine = get_engine()
        with engine.begin() as conn:
            mark_ats_synced(conn, company.get("company_ats_id"), success=False)
        return _finalize(
            {
                "fetched": 0,
                "normalized_count": 0,
                "accepted": 0,
                "skipped": 0,
                "error": error,
            }
        )

    engine = get_engine()
    metrics = IngestionMetrics()
    try:
        batch_size = 200
        for batch, fetch_error in _iter_job_batches(raw_jobs, batch_size):
            metrics.fetched += len(batch)
            if batch:
                batch_metrics = IngestionMetrics()
                with engine.begin() as conn:
                    process_company_jobs(
                        conn,
                        batch,
                        adapter,
                        company_id,
                        provider,
                        batch_metrics,
                    )
                _merge_metrics(metrics, batch_metrics)

            if fetch_error:
                with engine.begin() as conn:
                    mark_ats_synced(conn, company.get("company_ats_id"), success=False)
                result = metrics.to_result_dict()
                result["error"] = fetch_error.error_code
                return _finalize(result)

        with engine.begin() as conn:
            mark_ats_synced(conn, company.get("company_ats_id"), success=True)

    except Exception:
        logger.error(
            "employer ingestion transaction failed",
            exc_info=True,
            extra={
                "company_id": company_id,
                "ats_provider": provider,
                "ats_slug": ats_slug,
                **tick_context,
            },
        )
        return _finalize(
            {
                "fetched": metrics.fetched,
                "normalized_count": metrics.normalized,
                "accepted": metrics.accepted,
                "skipped": metrics.skipped,
                "error": "transaction_failed",
            }
        )

    return _finalize(metrics.to_result_dict())


def run_employer_ingestion() -> dict:
    started = perf_counter()
    engine = get_engine()
    companies_load_duration_ms = 0
    ingestion_loop_duration_ms = 0

    total_companies = 0
    companies_failed = 0
    companies_invalid_slug = 0
    synced_ats_count = 0
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
        tick_context = get_current_tick_context()
        companies_load_started = perf_counter()
        with engine.connect() as conn:
            companies = load_active_ats_companies(conn, limit=GLOBAL_COMPANIES_LIMIT)
        companies_load_duration_ms = int((perf_counter() - companies_load_started) * 1000)

        total_companies = len(companies)
        log_ingestion(
            source=SOURCE,
            phase="fetch",
            raw_count=total_companies,
            companies_processed=total_companies,
            companies_load_duration_ms=companies_load_duration_ms,
            **tick_context,
        )

        ingestion_loop_started = perf_counter()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        try:
            futures = {executor.submit(ingest_company, company): company for company in companies}
            # Bufor poniżej deadline Cloud Tasks (30 min) pozwala zalogować timeout
            # przed twardym ucięciem requestu HTTP przez platformę.
            for future in concurrent.futures.as_completed(
                futures,
                timeout=INGESTION_POOL_TIMEOUT_SECONDS,
            ):
                try:
                    result = future.result()

                    if "error" in result:
                        companies_failed += 1
                        if result.get("error") == "invalid_ats_slug":
                            companies_invalid_slug += 1
                        continue

                    synced_ats_count += 1
                    total_fetched += int(result.get("fetched", 0) or 0)
                    total_normalized += int(result.get("normalized_count", 0) or 0)
                    total_accepted += int(result.get("accepted", 0) or 0)
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
                    company_context = futures[future]
                    logger.error(
                        "employer ingestion thread pool future failed",
                        exc_info=True,
                        extra={
                            "company_id": str(company_context.get("company_id") or ""),
                            "ats_provider": company_context.get("ats_provider"),
                            "ats_slug": company_context.get("ats_slug"),
                            **tick_context,
                        },
                    )
                    companies_failed += 1
        except concurrent.futures.TimeoutError:
            logger.error(
                "employer_ingestion_pool_timeout",
                extra={
                    "msg": "Thread pool exceeded Cloud Tasks-compatible deadline",
                    "timeout_sec": INGESTION_POOL_TIMEOUT_SECONDS,
                    **tick_context,
                },
            )
        finally:
            # Niezwykle ważne: wait=False sprawi, że główny wątek (API/Worker) ucieknie
            # i dokończy tick, a cancel_futures przerwie oczekujące zadania w kolejce!
            executor.shutdown(wait=False, cancel_futures=True)
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
            synced_ats_count=synced_ats_count,
            hard_geo_rejected_count=total_hard_geo_rejected,
            companies_load_duration_ms=companies_load_duration_ms,
            ingestion_loop_duration_ms=ingestion_loop_duration_ms,
            duration_ms=duration_ms,
            error=str(exc),
            **tick_context,
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
        synced_ats_count=synced_ats_count,
        hard_geo_rejected_count=total_hard_geo_rejected,
        companies_load_duration_ms=companies_load_duration_ms,
        ingestion_loop_duration_ms=ingestion_loop_duration_ms,
        duration_ms=duration_ms,
        **tick_context,
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
            "synced_ats_count": synced_ats_count,
            "accepted_jobs": total_accepted,
            "hard_geo_rejected_count": total_hard_geo_rejected,
            "duration_ms": duration_ms,
            **tick_context,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
