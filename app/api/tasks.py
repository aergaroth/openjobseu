import logging
import time
import uuid
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.security.auth import require_internal_or_user_api_access
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

tasks_router = APIRouter(
    prefix="/tasks",
    tags=["internal-tasks"],
    dependencies=[Depends(require_internal_or_user_api_access)],
)

ASYNC_TASKS = {}

class DequeHandler(logging.Handler):
    def __init__(self, log_deque: deque):
        super().__init__()
        self.log_deque = log_deque

    def emit(self, record):
        try:
            self.log_deque.append(self.format(record))
        except Exception:
            self.handleError(record)

def background_runner(_task_id: str, func, *args, **kwargs):
    log_deque = deque(maxlen=200)
    handler = DequeHandler(log_deque)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    
    target_logger = logging.getLogger("openjobseu")
    target_logger.addHandler(handler)
    
    ASYNC_TASKS[_task_id]["log_deque"] = log_deque
    ASYNC_TASKS[_task_id]["status"] = "running"
    try:
        result = func(*args, **kwargs)
        if isinstance(result, dict) and result.get("status") == "cancelled":
            ASYNC_TASKS[_task_id]["status"] = "cancelled"
        else:
            ASYNC_TASKS[_task_id]["status"] = "completed"
        ASYNC_TASKS[_task_id]["result"] = result
    except Exception as e:
        logger.exception("Async task failed", extra={"task_id": _task_id, "error": str(e)})
        ASYNC_TASKS[_task_id]["status"] = "failed"
        ASYNC_TASKS[_task_id]["error"] = str(e)
    finally:
        target_logger.removeHandler(handler)
        logs = "\n".join(log_deque)
        if len(log_deque) == log_deque.maxlen:
            logs = "... [TRUNCATED] ...\n" + logs
        ASYNC_TASKS[_task_id]["logs"] = logs
        ASYNC_TASKS[_task_id].pop("log_deque", None)
        ASYNC_TASKS[_task_id]["finished_at"] = time.time()

def _cleanup_old_tasks(retention_seconds: float = 600.0):
    """Removes completed, failed, or cancelled tasks older than retention_seconds."""
    now = time.time()
    to_delete = []
    for tid, tdata in ASYNC_TASKS.items():
        if tdata.get("status") in ("completed", "failed", "cancelled"):
            if now - tdata.get("finished_at", now) > retention_seconds:
                to_delete.append(tid)
    for tid in to_delete:
        del ASYNC_TASKS[tid]

def run_backfill_compliance_task(limit: int = 10000, task_id: str = None):
    total = 0
    while total < limit:
        if task_id and ASYNC_TASKS.get(task_id, {}).get("cancel_requested"):
            logger.warning("backfill_compliance cancelled by user", extra={"task_id": task_id, "updated_jobs_count": total})
            return {"status": "cancelled", "updated_jobs_count": total}
        chunk = min(1000, limit - total)
        count = backfill_missing_compliance_classes(limit=chunk)
        if not count:
            break
        total += count
        logger.info("backfill_compliance chunk completed", extra={"chunk_updated": count, "total_updated": total})
    return {"status": "completed", "updated_jobs_count": total}

def run_backfill_salary_task(limit: int = 10000, task_id: str = None):
    total = 0
    while total < limit:
        if task_id and ASYNC_TASKS.get(task_id, {}).get("cancel_requested"):
            logger.warning("backfill_salary cancelled by user", extra={"task_id": task_id, "updated_jobs_count": total})
            return {"status": "cancelled", "updated_jobs_count": total}
        chunk = min(1000, limit - total)
        count = backfill_missing_salary_fields(limit=chunk)
        if not count:
            break
        total += count
        logger.info("backfill_salary chunk completed", extra={"chunk_updated": count, "total_updated": total})
    return {"status": "completed", "updated_jobs_count": total}

def run_tick_task(incremental: bool = True, limit: int = 100):
    employer_worker.GLOBAL_INCREMENTAL_FETCH = incremental
    employer_worker.GLOBAL_COMPANIES_LIMIT = limit
    return run_pipeline(group="all")

@tasks_router.post("/{task_name}")
def trigger_async_task(task_name: str, background_tasks: BackgroundTasks, incremental: bool = Query(True, description="Only for 'tick' task"), limit: int = Query(100, description="Limit parameter for tick and backfill tasks")):
    _cleanup_old_tasks()
    task_map = {"tick": run_tick_task, "discovery": run_discovery_pipeline, "careers": run_careers_discovery, "guess": run_ats_guessing, "ats-reverse": run_ats_reverse_discovery, "company-sources": run_company_source_discovery, "dorking": run_dorking_discovery, "backfill-department": backfill_missing_departments, "backfill-compliance": run_backfill_compliance_task, "backfill-salary": run_backfill_salary_task}
    if task_name not in task_map:
        raise HTTPException(status_code=404, detail="Task not found")
    for tdata in ASYNC_TASKS.values():
        if tdata.get("task") == task_name and tdata.get("status") in ("pending", "running"):
            raise HTTPException(status_code=409, detail=f"Task {task_name} is already running")
    task_id = str(uuid.uuid4())
    ASYNC_TASKS[task_id] = {"status": "pending", "task": task_name}
    if task_name == "tick":
        background_tasks.add_task(background_runner, task_id, task_map[task_name], incremental=incremental, limit=limit)
    elif task_name in ("backfill-compliance", "backfill-salary"):
        background_tasks.add_task(background_runner, task_id, task_map[task_name], limit=limit, task_id=task_id)
    else:
        background_tasks.add_task(background_runner, task_id, task_map[task_name])
    return {"task_id": task_id, "status": "pending", "task": task_name}

@tasks_router.post("/{task_id}/cancel")
def cancel_async_task(task_id: str):
    if task_id not in ASYNC_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    if ASYNC_TASKS[task_id].get("status") in ("pending", "running"):
        ASYNC_TASKS[task_id]["cancel_requested"] = True
        return {"status": "cancel_requested"}
    return {"status": ASYNC_TASKS[task_id].get("status")}

@tasks_router.get("/{task_id}")
def get_task_status(task_id: str):
    if task_id not in ASYNC_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    task_data = ASYNC_TASKS[task_id].copy()
    if "log_deque" in task_data:
        logs = "\n".join(task_data["log_deque"])
        if len(task_data["log_deque"]) == task_data["log_deque"].maxlen:
            logs = "... [TRUNCATED] ...\n" + logs
        task_data["logs"] = logs
        task_data.pop("log_deque", None)
    return task_data