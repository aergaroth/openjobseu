import json
import logging
import os
import re
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request, Response, status


from app.logging import should_use_text_logs
from app.utils.cloud_tasks import create_tick_task, is_tick_queue_configured
from app.utils.tick_context import build_tick_context
from app.utils.tick_formatting import format_tick_summary
import app.adapters.ats as ats  # noqa: F401
from app.adapters.ats.registry import get_adapter
from app.workers.pipeline import run_pipeline

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_salary import backfill_missing_salary_fields
from app.utils.backfill_department import backfill_missing_departments
from storage.repositories.market_repository import backfill_remote_ratio
from storage.repositories.system_repository import get_system_metrics
from storage.db_engine import get_engine

from app.domain.jobs.job_processing import process_ingested_job
import app.workers.ingestion.employer as employer_worker

logger = logging.getLogger("openjobseu.runtime")

system_ops_router = APIRouter(tags=["internal-system-ops"])
system_hybrid_router = APIRouter(tags=["internal-system-hybrid"])

TICK_SOURCE = "employer_ing"


class BackfillResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    updated_jobs_count: int


@system_hybrid_router.get("/metrics", response_model=dict[str, Any])
def internal_metrics():
    return get_system_metrics()


@system_ops_router.post("/backfill-compliance", response_model=BackfillResponse)
def backfill_compliance(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_compliance_classes(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@system_ops_router.post("/backfill-salary", response_model=BackfillResponse)
def backfill_salary(limit: int = Query(1000, ge=1, le=10000)):
    result = backfill_missing_salary_fields(limit=limit)
    return {"status": "ok", "updated_jobs_count": result["updated"]}


@system_ops_router.post("/backfill-department", response_model=BackfillResponse)
def backfill_department():
    updated_count = backfill_missing_departments()
    return {"status": "ok", "updated_jobs_count": updated_count}


@system_ops_router.post("/backfill-remote-ratio", response_model=BackfillResponse)
def backfill_remote_ratio_endpoint():
    engine = get_engine()
    with engine.begin() as conn:
        updated_count = backfill_remote_ratio(conn)
    return {"status": "ok", "updated_jobs_count": updated_count}


def _strip_html(obj):
    if isinstance(obj, dict):
        return {k: _strip_html(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_html(v) for v in obj]
    elif isinstance(obj, str):
        return re.sub(r"<[^>]+>", "", obj)
    return obj


@system_hybrid_router.post("/preview-job")
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


@system_ops_router.post("/tick", response_model=dict[str, Any])
def manual_tick(
    request: Request,
    response_format: str = Query("auto", alias="format", pattern="^(auto|text|json)$"),
    group: str = Query("all", pattern="^(all|ingestion|maintenance)$"),
    incremental: bool = Query(True, description="Enable incremental fetch based on last sync date"),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Limit the number of companies processed in this tick",
    ),
):
    return tick(
        request=request,
        response_format=response_format,
        group=group,
        incremental=incremental,
        limit=limit,
    )


@system_ops_router.post("/tick/execute", response_model=dict[str, Any])
async def execute_tick(request: Request):
    body = await request.json()
    group = body.get("group", "all")
    incremental = bool(body.get("incremental", True))
    limit = int(body.get("limit", 100))
    response_format = body.get("response_format", "json")

    context = build_tick_context(
        request=request,
        request_id=request.headers.get("x-request-id") or body.get("request_id"),
        tick_id=request.headers.get("x-tick-id") or body.get("tick_id"),
        group=group,
        incremental=incremental,
        limit=limit,
        execution_mode="async_task",
        trigger_source="cloud_tasks",
        scheduler_job_name=request.headers.get("x-scheduler-job-name") or body.get("scheduler_job_name"),
        scheduler_schedule_time=request.headers.get("x-scheduler-schedule-time") or body.get("scheduler_schedule_time"),
        task_name=request.headers.get("x-cloudtasks-taskname"),
    )
    return _execute_tick(response_format=response_format, force_text=False, context=context)


def tick(
    *,
    request: Request | None = None,
    response_format: str = "auto",
    force_text: bool = False,
    group: str = "all",
    incremental: bool = True,
    limit: int = 100,
):
    queue_configured = is_tick_queue_configured() and request is not None
    context = build_tick_context(
        request=request,
        group=group,
        incremental=incremental,
        limit=limit,
        execution_mode="async_trigger" if queue_configured else "sync_request",
        trigger_source=(
            "cloud_scheduler"
            if request is not None and request.headers.get("x-cloudscheduler-jobname")
            else "manual_request"
        ),
    )

    if queue_configured:
        return _enqueue_tick(
            request=request,
            response_format=response_format,
            force_text=force_text,
            context=context,
        )

    return _execute_tick(
        response_format=response_format,
        force_text=force_text,
        context={
            **context,
            "execution_mode": "sync_request",
            "trigger_source": "direct_request",
        },
    )


def _enqueue_tick(*, request: Request, response_format: str, force_text: bool, context: dict):
    query = urlencode({"group": context["group"]})
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
    handler_url = f"{base_url}/internal/tick/execute?{query}"
    try:
        task_response = create_tick_task(
            task_id=context["tick_id"],
            handler_url=handler_url,
            payload={
                "tick_id": context["tick_id"],
                "request_id": context["request_id"],
                "group": context["group"],
                "incremental": context["incremental"],
                "limit": context["limit"],
                "response_format": "json",
                "scheduler_job_name": context.get("scheduler_job_name"),
                "scheduler_schedule_time": context.get("scheduler_schedule_time"),
            },
            headers={
                "Content-Type": "application/json",
                "X-Request-Id": context["request_id"],
                "X-Tick-Id": context["tick_id"],
                "X-Scheduler-Job-Name": context.get("scheduler_job_name", ""),
                "X-Scheduler-Schedule-Time": context.get("scheduler_schedule_time", ""),
            },
        )
    except Exception:
        logger.exception("Failed to enqueue tick task in Cloud Tasks")
        raise HTTPException(status_code=500, detail="Failed to enqueue task in Cloud Tasks")

    payload = {
        "status": "accepted",
        "phase": "trigger_accepted",
        "mode": "prod",
        "sources": [TICK_SOURCE] if context["group"] in ("all", "ingestion") else [],
        "tick_id": context["tick_id"],
        "request_id": context["request_id"],
        "group": context["group"],
        "incremental": context["incremental"],
        "limit": context["limit"],
        "scheduler_job_name": context.get("scheduler_job_name"),
        "scheduler_schedule_time": context.get("scheduler_schedule_time"),
        "scheduler_execution": context.get("scheduler_execution"),
        "task_name": task_response.get("name"),
    }

    logger.info("tick_trigger_accepted", extra={"component": "runtime", **payload})

    render_mode = (response_format or "auto").strip().lower()
    if force_text:
        render_mode = "text"
    if render_mode == "text" or (render_mode == "auto" and should_use_text_logs()):
        return Response(
            content=format_tick_summary(payload),
            media_type="text/plain",
            status_code=status.HTTP_202_ACCEPTED,
        )

    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/json",
        status_code=status.HTTP_202_ACCEPTED,
    )


def _execute_tick(*, response_format: str, force_text: bool, context: dict):
    ingestion_mode = "prod"
    tick_sources = [TICK_SOURCE] if context["group"] in ("all", "ingestion") else []
    employer_worker.GLOBAL_INCREMENTAL_FETCH = context["incremental"]
    employer_worker.GLOBAL_COMPANIES_LIMIT = context["limit"]

    logger.info(
        "tick_execution_started",
        extra={
            "component": "runtime",
            "phase": "tick_execution_started",
            "mode": ingestion_mode,
            "sources": tick_sources,
            **context,
        },
    )

    result = run_pipeline(group=context["group"], context=context)

    payload = {
        "status": "completed",
        "phase": "pipeline_completed",
        "mode": ingestion_mode,
        "sources": tick_sources,
        **result,
    }

    render_mode = (response_format or "auto").strip().lower()
    if force_text:
        render_mode = "text"
    if render_mode == "text" or (render_mode == "auto" and should_use_text_logs()):
        return Response(content=format_tick_summary(payload), media_type="text/plain")

    return payload
