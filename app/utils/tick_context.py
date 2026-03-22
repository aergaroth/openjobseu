from __future__ import annotations

import os
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request

CURRENT_TICK_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("current_tick_context", default={})


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def ensure_request_id(request: Request | None = None) -> str:
    if request is not None:
        for header_name in ("x-request-id", "x-cloud-trace-context"):
            header_value = _clean(request.headers.get(header_name))
            if header_value:
                if header_name == "x-cloud-trace-context":
                    return header_value.split("/", 1)[0]
                return header_value
    return str(uuid.uuid4())


def scheduler_execution_id(job_name: str | None, schedule_time: str | None) -> str | None:
    if job_name and schedule_time:
        return f"{job_name}@{schedule_time}"
    if job_name:
        return job_name
    if schedule_time:
        return schedule_time
    return None


def build_tick_context(
    *,
    request: Request | None = None,
    request_id: str | None = None,
    tick_id: str | None = None,
    group: str = "all",
    incremental: bool = True,
    limit: int = 100,
    execution_mode: str,
    trigger_source: str,
    scheduler_job_name: str | None = None,
    scheduler_schedule_time: str | None = None,
    task_name: str | None = None,
) -> dict[str, Any]:
    request_id = _clean(request_id) or ensure_request_id(request)
    tick_id = _clean(tick_id) or str(uuid.uuid4())

    if request is not None:
        scheduler_job_name = scheduler_job_name or _clean(request.headers.get("x-cloudscheduler-jobname"))
        scheduler_schedule_time = scheduler_schedule_time or _clean(
            request.headers.get("x-cloudscheduler-scheduletime")
        )
        task_name = task_name or _clean(request.headers.get("x-cloudtasks-taskname"))

    context = {
        "request_id": request_id,
        "tick_id": tick_id,
        "group": group,
        "incremental": incremental,
        "limit": limit,
        "execution_mode": execution_mode,
        "trigger_source": trigger_source,
        "scheduler_job_name": scheduler_job_name,
        "scheduler_schedule_time": scheduler_schedule_time,
        "scheduler_execution": scheduler_execution_id(scheduler_job_name, scheduler_schedule_time),
        "task_name": task_name,
        "service_runtime": _clean(os.getenv("K_SERVICE")),
    }
    return {key: value for key, value in context.items() if value is not None}


def set_current_tick_context(context: dict[str, Any]):
    return CURRENT_TICK_CONTEXT.set(dict(context))


def reset_current_tick_context(token) -> None:
    CURRENT_TICK_CONTEXT.reset(token)


def get_current_tick_context() -> dict[str, Any]:
    return dict(CURRENT_TICK_CONTEXT.get())
