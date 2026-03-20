import logging
import re
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.security.auth import require_internal_or_user_api_access

from app.logging import should_use_text_logs
from app.utils.tick_formatting import format_tick_summary
import app.adapters.ats as ats  # noqa: F401
from app.adapters.ats.registry import get_adapter
from app.workers.pipeline import run_pipeline

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_salary import backfill_missing_salary_fields
from app.utils.backfill_department import backfill_missing_departments
from storage.repositories.system_repository import get_system_metrics

from app.domain.jobs.job_processing import process_ingested_job
import app.workers.ingestion.employer as employer_worker

logger = logging.getLogger("openjobseu.runtime")

system_router = APIRouter(
    tags=["internal-system"],
    dependencies=[Depends(require_internal_or_user_api_access)],
)

TICK_SOURCE = "employer_ing"


@system_router.get("/metrics")
def internal_metrics():
    return get_system_metrics()


@system_router.post("/backfill-compliance")
def backfill_compliance(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_compliance_classes(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@system_router.post("/backfill-salary")
def backfill_salary(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_salary_fields(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@system_router.post("/backfill-department")
def backfill_department():
    updated_count = backfill_missing_departments()
    return {"status": "ok", "updated_jobs_count": updated_count}


def _strip_html(obj):
    if isinstance(obj, dict):
        return {k: _strip_html(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_html(v) for v in obj]
    elif isinstance(obj, str):
        return re.sub(r"<[^>]+>", "", obj)
    return obj


@system_router.post("/preview-job")
def preview_job_endpoint(provider: str, slug: str, job_id: str | None = None):
    try:
        adapter = get_adapter(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    output = [f"Fetching jobs for '{slug}' via '{provider}'...\n"]
    
    try:
        raw_jobs = adapter.fetch({"ats_slug": slug})
    except Exception as e:
        output.append(f"Failed to fetch jobs: {e}")
        return Response(content="\n".join(output), media_type="text/plain")

    if not raw_jobs:
        output.append("No jobs found for this slug.")
        return Response(content="\n".join(output), media_type="text/plain")

    found = False
    for raw_job in raw_jobs:
        normalized = adapter.normalize(raw_job)
        if not normalized:
            continue
        
        if job_id and str(normalized.get("source_job_id")) != str(job_id):
            continue

        found = True
        output.append("=" * 80)
        output.append(f"RAW JOB PAYLOAD (ID: {normalized.get('source_job_id')}):")
        display_raw = _strip_html(raw_job)
        raw_json = json.dumps(display_raw, indent=2, ensure_ascii=False)
        output.append(raw_json[:3000] + ("\n... [TRUNCATED]" if len(raw_json) > 3000 else ""))

        output.append("\n" + "=" * 80)
        output.append("COMPLIANCE & PROCESSING REPORT:")
        processed_job, report = process_ingested_job(normalized, source=f"debug:{provider}")
        
        output.append(json.dumps(report, indent=2, ensure_ascii=False))
        
        output.append("\nPROCESSED JOB (FINAL):")
        if processed_job:
            processed_job.pop("description", None)  # Omit long description for terminal readability
            output.append(json.dumps(processed_job, indent=2, ensure_ascii=False))
        else:
            output.append("Job was REJECTED by policy engine and returned None.")

        break

    if not found:
        output.append(f"No matching job found (checked {len(raw_jobs)} jobs).")

    return Response(content="\n".join(output), media_type="text/plain")


@system_router.post("/tick")
def manual_tick(response_format: str = Query("auto", alias="format", pattern="^(auto|text|json)$"), group: str = Query("all", pattern="^(all|ingestion|maintenance)$"), incremental: bool = Query(True, description="Enable incremental fetch based on last sync date"), limit: int = Query(100, ge=1, le=1000, description="Limit the number of companies processed in this tick")):
    return tick(response_format=response_format, group=group, incremental=incremental, limit=limit)


def tick(*, response_format: str = "auto", force_text: bool = False, group: str = "all", incremental: bool = True, limit: int = 100):
    ingestion_mode = "prod"
    tick_sources = [TICK_SOURCE] if group in ("all", "ingestion") else []
    employer_worker.GLOBAL_INCREMENTAL_FETCH = incremental
    employer_worker.GLOBAL_COMPANIES_LIMIT = limit

    logger.info("tick_start", extra={"component": "runtime", "phase": "tick_start", "mode": ingestion_mode, "sources": tick_sources, "group": group, "incremental": incremental, "limit": limit})

    result = run_pipeline(group=group)

    payload = {"status": "ok", "mode": ingestion_mode, "sources": tick_sources, **result}

    render_mode = (response_format or "auto").strip().lower()
    if force_text:
        render_mode = "text"
    if render_mode == "text" or (render_mode == "auto" and should_use_text_logs()):
        return Response(content=format_tick_summary(payload), media_type="text/plain")

    return payload