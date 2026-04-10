import asyncio
import os
import json
import logging
import uuid

from pydantic import BaseModel, ConfigDict
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.utils.cloud_tasks import create_tick_task, is_tick_queue_configured
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.pipeline import run_discovery_pipeline
from app.workers.discovery.company_sources import run_company_source_discovery
from app.workers.discovery.ats_reverse import run_ats_reverse_discovery
from app.workers.discovery.dorking import run_dorking_discovery
from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_salary import backfill_missing_salary_fields
from app.utils.backfill_department import backfill_missing_departments
from app.workers.pipeline import run_pipeline
import app.workers.ingestion.employer as employer_worker

logger = logging.getLogger("openjobseu.runtime")

tasks_trigger_router = APIRouter(
    prefix="/tasks",
    tags=["internal-tasks"],
)

tasks_execute_router = APIRouter(
    prefix="/tasks",
    tags=["internal-tasks"],
)


class TaskTriggerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str
    status: str
    task: str
    cloud_task_name: str | None = None
    result: Any | None = None


class TaskExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    result: Any


def run_backfill_compliance_task(limit: int = 5000):
    count = backfill_missing_compliance_classes(limit=limit)
    logger.info("backfill_compliance completed", extra={"updated_jobs_count": count, "limit": limit})
    return {"status": "completed", "updated_jobs_count": count}


def run_backfill_salary_task(limit: int = 5000):
    result = backfill_missing_salary_fields(limit=limit)
    logger.info("backfill_salary completed", extra={"updated_jobs_count": result["updated"], "limit": limit})
    return {"status": "completed", "processed_jobs_count": result["processed"], "updated_jobs_count": result["updated"]}


def run_tick_task(incremental: bool = True, limit: int = 100):
    employer_worker.GLOBAL_INCREMENTAL_FETCH = incremental
    employer_worker.GLOBAL_COMPANIES_LIMIT = limit
    return run_pipeline(group="all")


TASK_MAP = {
    "tick": run_tick_task,
    "discovery": run_discovery_pipeline,
    "careers": run_careers_discovery,
    "guess": run_ats_guessing,
    "ats-reverse": run_ats_reverse_discovery,
    "company-sources": run_company_source_discovery,
    "dorking": run_dorking_discovery,
    "backfill-department": backfill_missing_departments,
    "backfill-compliance": run_backfill_compliance_task,
    "backfill-salary": run_backfill_salary_task,
}


@tasks_trigger_router.post("/{task_name}", response_model=TaskTriggerResponse)
def trigger_async_task(
    task_name: str,
    request: Request,
    incremental: bool = Query(True, description="Only for 'tick' task"),
    limit: int = Query(100, description="Limit parameter for tick and backfill tasks"),
):
    if task_name not in TASK_MAP:
        raise HTTPException(status_code=404, detail="Task not found")

    task_id = str(uuid.uuid4())

    if is_tick_queue_configured():
        base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
        handler_url = f"{base_url}/internal/tasks/{task_name}/execute"

        payload = {"incremental": incremental, "limit": limit}
        headers = {"Content-Type": "application/json"}

        try:
            task_response = create_tick_task(
                task_id=task_id,
                handler_url=handler_url,
                payload=payload,
                headers=headers,
            )
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_name}", extra={"error": str(e)})
            raise HTTPException(status_code=500, detail="Failed to enqueue task in Cloud Tasks")

        logger.info(
            "task_enqueued",
            extra={
                "task": task_name,
                "task_id": task_id,
                "handler_url": handler_url,
                "cloud_task_name": task_response.get("name"),
            },
        )

        return Response(
            content=json.dumps(
                {
                    "task_id": task_id,
                    "status": "enqueued",
                    "task": task_name,
                    "cloud_task_name": task_response.get("name"),
                }
            ),
            media_type="application/json",
            status_code=status.HTTP_202_ACCEPTED,
        )

    # Fallback synchroniczny dla testów / środowiska lokalnego bez Cloud Tasks
    logger.info("Executing task synchronously (no queue configured)", extra={"task": task_name})
    func = TASK_MAP[task_name]

    if task_name == "tick":
        result = func(incremental=incremental, limit=limit)
    elif task_name in ("backfill-compliance", "backfill-salary"):
        result = func(limit=limit)
    else:
        result = func()

    return {
        "task_id": task_id,
        "status": "completed",
        "task": task_name,
        "result": result,
    }


def _enqueue_task_continuation(task_name: str, limit: int, request: Request) -> None:
    """Re-enqueue a backfill task when it hit the per-run record cap."""
    task_id = str(uuid.uuid4())
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
    handler_url = f"{base_url}/internal/tasks/{task_name}/execute"
    try:
        create_tick_task(
            task_id=task_id,
            handler_url=handler_url,
            payload={"limit": limit},
            headers={"Content-Type": "application/json"},
        )
        logger.info(
            "task_continuation_enqueued",
            extra={"task": task_name, "task_id": task_id, "limit": limit},
        )
    except Exception:
        logger.error(
            "task_continuation_enqueue_failed",
            extra={"task": task_name},
            exc_info=True,
        )


# Tasks that support self-chaining when they hit their per-run record cap.
_CHAINABLE_BACKFILL_TASKS = {"backfill-compliance", "backfill-salary"}


@tasks_execute_router.post("/{task_name}/execute", response_model=TaskExecuteResponse)
async def execute_task(task_name: str, request: Request):
    if task_name not in TASK_MAP:
        raise HTTPException(status_code=404, detail="Task not found")

    body = await request.json()
    incremental = body.get("incremental", True)
    limit = body.get("limit", 100)

    func = TASK_MAP[task_name]
    try:
        if task_name == "tick":
            result = await asyncio.to_thread(func, incremental=incremental, limit=limit)
        elif task_name in _CHAINABLE_BACKFILL_TASKS:
            result = await asyncio.to_thread(func, limit=limit)
            # Self-chain: if the batch hit the cap AND made progress, more records likely remain.
            # Without the progress check (updated > 0), tasks with no parseable records would
            # re-fetch the same records and loop indefinitely.
            processed = result.get("processed_jobs_count", 0) if isinstance(result, dict) else 0
            updated = result.get("updated_jobs_count", 0) if isinstance(result, dict) else 0
            if processed >= limit and updated > 0 and is_tick_queue_configured():
                _enqueue_task_continuation(task_name, limit, request)
        else:
            result = await asyncio.to_thread(func)

        return {"status": "completed", "result": result}
    except Exception as e:
        logger.exception(f"Task {task_name} execution failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
