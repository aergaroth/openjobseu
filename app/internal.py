import logging
import os
from collections import deque
import uuid
import time
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import HTMLResponse

from app.security.auth import (
    require_internal_or_user_api_access,
    require_user_api_access,
    require_user_login,
)
from app.domain.compliance.audit_filter_registry import get_audit_filter_registry
from app.logging import should_use_text_logs
from app.utils.tick_formatting import format_tick_summary
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.pipeline import run_discovery_pipeline
from app.workers.discovery.company_sources import run_company_source_discovery
from app.workers.discovery.ats_reverse import run_ats_reverse_discovery
from app.adapters.ats.greenhouse import GreenhouseAdapter
from app.adapters.ats.lever import LeverAdapter
from app.adapters.ats.workable import WorkableAdapter
from app.adapters.ats.ashby import AshbyAdapter
from app.workers.pipeline import run_pipeline
from storage.db_logic import (
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_audit_source_filter_values,
    get_jobs_audit,
    get_failing_ats_integrations,
    get_ats_integration_by_id,
    deactivate_ats_integration,
)

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_salary import backfill_missing_salary_fields
from app.utils.backfill_department import backfill_missing_departments
from storage.repositories.discovery_repository import (
    get_discovered_company_ats,
    get_discovery_candidates,
)
from storage.db_engine import get_engine

from app.security.internal_access import require_internal_access

logger = logging.getLogger("openjobseu.runtime")

ADAPTER_MAP = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "workable": WorkableAdapter,
    "ashby": AshbyAdapter,
}

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PANEL_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.html"
AUDIT_PANEL_JS_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.js"
AUDIT_PANEL_CSS_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.css"
TICK_SOURCE = "employer_ing"


@lru_cache(maxsize=8)
def _cached_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_audit_panel_html() -> str:
    if os.environ.get("APP_RUNTIME") == "local":
        return AUDIT_PANEL_PATH.read_text(encoding="utf-8")
    return _cached_read_text(AUDIT_PANEL_PATH)


def _load_audit_panel_js() -> str:
    if os.environ.get("APP_RUNTIME") == "local":
        return AUDIT_PANEL_JS_PATH.read_text(encoding="utf-8")
    return _cached_read_text(AUDIT_PANEL_JS_PATH)


def _load_audit_panel_css() -> str:
    if os.environ.get("APP_RUNTIME") == "local":
        return AUDIT_PANEL_CSS_PATH.read_text(encoding="utf-8")
    return _cached_read_text(AUDIT_PANEL_CSS_PATH)


@router.get("/audit", response_class=HTMLResponse, dependencies=[Depends(require_user_login)])
def audit_panel():
    try:
        content = _load_audit_panel_html()
    except OSError:
        logger.exception("failed to load audit panel html", extra={"path": str(AUDIT_PANEL_PATH)})
        raise HTTPException(status_code=500, detail="audit panel template not available")

    return HTMLResponse(content=content)


@router.get("/audit/script.js", dependencies=[Depends(require_user_login)])
def audit_panel_js():
    try:
        content = _load_audit_panel_js()
    except OSError:
        logger.exception("failed to load audit panel js", extra={"path": str(AUDIT_PANEL_JS_PATH)})
        raise HTTPException(status_code=500, detail="audit panel script not available")

    return Response(content=content, media_type="application/javascript")


@router.get("/audit/style.css", dependencies=[Depends(require_user_login)])
def audit_panel_css():
    try:
        content = _load_audit_panel_css()
    except OSError:
        logger.exception("failed to load audit panel css", extra={"path": str(AUDIT_PANEL_CSS_PATH)})
        raise HTTPException(status_code=500, detail="audit panel style not available")

    return Response(content=content, media_type="text/css")

@router.get("/audit/jobs", dependencies=[Depends(require_user_api_access)])
def audit_jobs(
    status: str | None = Query(None),
    source: str | None = Query(None),
    company: str | None = Query(None),
    title: str | None = Query(None),
    remote_scope: str | None = Query(None),
    remote_class: str | None = Query(None),
    geo_class: str | None = Query(None),
    compliance_status: str | None = Query(None),
    min_compliance_score: int | None = Query(None, ge=0, le=100),
    max_compliance_score: int | None = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return get_jobs_audit(
        status=status,
        source=source,
        company=company,
        title=title,
        remote_scope=remote_scope,
        remote_class=remote_class,
        geo_class=geo_class,
        compliance_status=compliance_status,
        min_compliance_score=min_compliance_score,
        max_compliance_score=max_compliance_score,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/filters", dependencies=[Depends(require_user_api_access)])
def audit_filter_registry():
    payload = get_audit_filter_registry()
    payload["source"] = get_audit_source_filter_values()
    return payload


@router.get("/audit/stats/company", dependencies=[Depends(require_user_api_access)])
def audit_company_stats(
    min_total_jobs: int = Query(10, ge=0, le=10000),
):
    return {
        "min_total_jobs": int(min_total_jobs),
        "items": get_audit_company_compliance_stats(min_total_jobs=min_total_jobs),
    }


@router.get("/audit/stats/source-7d", dependencies=[Depends(require_user_api_access)])
def audit_source_stats_7d():
    return {
        "window": "last_7_days",
        "items": get_audit_source_compliance_stats_last_7d(),
    }


@router.get("/metrics", dependencies=[Depends(require_user_api_access)])
def internal_metrics():
    engine = get_engine()
    query = """
        SELECT 
            (SELECT COUNT(*) FROM jobs) as jobs_total,
            (SELECT COUNT(*) FROM jobs WHERE first_seen_at >= NOW() - INTERVAL '24 hours') as jobs_24h,
            (SELECT COUNT(*) FROM companies) as companies_total,
            (SELECT COUNT(*) FROM companies WHERE created_at >= NOW() - INTERVAL '24 hours') as companies_24h,
            (SELECT COUNT(*) FROM company_ats) as company_ats_total,
            (SELECT COUNT(*) FROM company_ats WHERE created_at >= NOW() - INTERVAL '24 hours') as company_ats_24h,
            (SELECT MAX(last_seen_at) FROM jobs) as last_tick_at
    """
    with engine.connect() as conn:
        row = conn.execute(text(query)).mappings().first()

    return {
        "jobs_total": row["jobs_total"] if row else 0,
        "jobs_24h": row["jobs_24h"] if row else 0,
        "companies_total": row["companies_total"] if row else 0,
        "companies_24h": row["companies_24h"] if row else 0,
        "company_ats_total": row["company_ats_total"] if row else 0,
        "company_ats_24h": row["company_ats_24h"] if row else 0,
        "last_tick_at": row["last_tick_at"].isoformat() if row and row["last_tick_at"] else None,
    }


@router.get("/discovery/audit", dependencies=[Depends(require_user_api_access)])
def discovery_audit():
    results = get_discovered_company_ats(limit=100)
    return {
        "count": len(results),
        "results": results,
    }


@router.get("/discovery/candidates", dependencies=[Depends(require_user_api_access)])
def discovery_candidates():
    results = get_discovery_candidates(limit=50)
    return {
        "count": len(results),
        "results": results,
    }


@router.post("/discovery/careers", dependencies=[Depends(require_internal_or_user_api_access)])
def run_careers():
    metrics = run_careers_discovery()
    return {
        "pipeline": "discovery",
        "phase": "careers_discovery",
        "metrics": metrics,
    }


@router.post("/discovery/guess", dependencies=[Depends(require_internal_or_user_api_access)])
def run_guessing():
    metrics = run_ats_guessing()
    return {
        "pipeline": "discovery",
        "phase": "ats_guessing",
        "metrics": metrics,
    }


@router.post("/discovery/ats-reverse", dependencies=[Depends(require_internal_or_user_api_access)])
def run_ats_reverse():
    metrics = run_ats_reverse_discovery()
    return {
        "pipeline": "discovery",
        "phase": "ats_reverse",
        "metrics": metrics,
    }


@router.post("/discovery/run", dependencies=[Depends(require_internal_or_user_api_access)])
def run_discovery():
    return run_discovery_pipeline()


@router.post("/discovery/company-sources", dependencies=[Depends(require_internal_or_user_api_access)])
def run_company_sources():
    return run_company_source_discovery()


@router.post("/audit/tick-dev", dependencies=[Depends(require_user_api_access)])
def run_tick_from_audit():
    result = tick(force_text=True)
    if isinstance(result, Response):
        return result
    if isinstance(result, str):
        return Response(content=result, media_type="text/plain")
    return result


@router.post("/backfill-compliance", dependencies=[Depends(require_internal_or_user_api_access)])
def backfill_compliance(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_compliance_classes(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@router.post("/backfill-salary", dependencies=[Depends(require_internal_or_user_api_access)])
def backfill_salary(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_salary_fields(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@router.post("/backfill-department", dependencies=[Depends(require_internal_or_user_api_access)])
def backfill_department():
    updated_count = backfill_missing_departments()
    return {"status": "ok", "updated_jobs_count": updated_count}


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

def background_runner(task_id: str, func, *args, **kwargs):
    log_deque = deque(maxlen=200)
    handler = DequeHandler(log_deque)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    
    target_logger = logging.getLogger("openjobseu")
    target_logger.addHandler(handler)
    
    ASYNC_TASKS[task_id]["log_deque"] = log_deque
    ASYNC_TASKS[task_id]["status"] = "running"
    try:
        result = func(*args, **kwargs)
        ASYNC_TASKS[task_id]["status"] = "completed"
        ASYNC_TASKS[task_id]["result"] = result
    except Exception as e:
        logger.exception("Async task failed", extra={"task_id": task_id, "error": str(e)})
        ASYNC_TASKS[task_id]["status"] = "failed"
        ASYNC_TASKS[task_id]["error"] = str(e)
    finally:
        target_logger.removeHandler(handler)
        logs = "\n".join(log_deque)
        if len(log_deque) == log_deque.maxlen:
            logs = "... [TRUNCATED] ...\n" + logs
        ASYNC_TASKS[task_id]["logs"] = logs
        ASYNC_TASKS[task_id].pop("log_deque", None)
        ASYNC_TASKS[task_id]["finished_at"] = time.time()


def _cleanup_old_tasks(retention_seconds: float = 600.0):
    """Removes completed or failed tasks older than retention_seconds."""
    now = time.time()
    to_delete = []
    for tid, tdata in ASYNC_TASKS.items():
        if tdata.get("status") in ("completed", "failed"):
            if now - tdata.get("finished_at", now) > retention_seconds:
                to_delete.append(tid)
    for tid in to_delete:
        del ASYNC_TASKS[tid]

@router.post("/tasks/{task_name}", dependencies=[Depends(require_internal_or_user_api_access)])
def trigger_async_task(task_name: str, background_tasks: BackgroundTasks):
    _cleanup_old_tasks()
    task_map = {
        "discovery": run_discovery_pipeline,
        "careers": run_careers_discovery,
        "guess": run_ats_guessing,
        "ats-reverse": run_ats_reverse_discovery,
        "company-sources": run_company_source_discovery,
        "backfill-department": backfill_missing_departments,
        "backfill-compliance": backfill_missing_compliance_classes,
        "backfill-salary": backfill_missing_salary_fields,
    }
    if task_name not in task_map:
        raise HTTPException(status_code=404, detail="Task not found")

    for tdata in ASYNC_TASKS.values():
        if tdata.get("task") == task_name and tdata.get("status") in ("pending", "running"):
            raise HTTPException(status_code=409, detail=f"Task {task_name} is already running")

    task_id = str(uuid.uuid4())
    ASYNC_TASKS[task_id] = {"status": "pending", "task": task_name}
    background_tasks.add_task(background_runner, task_id, task_map[task_name])
    return {"task_id": task_id, "status": "pending", "task": task_name}

@router.get("/tasks/{task_id}", dependencies=[Depends(require_internal_or_user_api_access)])
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

@router.get("/audit/ats-health", dependencies=[Depends(require_user_api_access)])
def audit_ats_health(days_threshold: int = Query(3, ge=1, le=30)):
    results = get_failing_ats_integrations(days_threshold=days_threshold)
    return {
        "days_threshold": days_threshold,
        "count": len(results),
        "items": results,
    }


@router.post("/audit/ats-deactivate/{company_ats_id}", dependencies=[Depends(require_user_api_access)])
def api_deactivate_ats(company_ats_id: str):
    with get_engine().begin() as conn:
        deactivate_ats_integration(conn, company_ats_id)
    return {"status": "ok", "company_ats_id": company_ats_id}


@router.post("/audit/ats-force-sync/{company_ats_id}", dependencies=[Depends(require_user_api_access)])
def api_force_sync_ats(company_ats_id: str):
    with get_engine().connect() as conn:
        ats_integration = get_ats_integration_by_id(conn, company_ats_id)
        if not ats_integration:
            raise HTTPException(status_code=404, detail="ATS integration not found")

    provider = ats_integration["ats_provider"]
    adapter_cls = ADAPTER_MAP.get(provider)
    if not adapter_cls:
        raise HTTPException(status_code=400, detail=f"No adapter found for provider: {provider}")

    adapter = adapter_cls()
    company_dict = {
        "ats_slug": ats_integration["ats_slug"],
        "company_id": ats_integration["company_id"],
        "legal_name": ats_integration["legal_name"],
    }

    try:
        raw_jobs = adapter.fetch(company_dict, updated_since=None)
        job_count = len(raw_jobs)
        return Response(content=f"Force sync successful. Fetched {job_count} jobs.", media_type="text/plain")
    except Exception as e:
        logger.error(f"Force sync failed for {company_ats_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")


@router.post("/tick", dependencies=[Depends(require_internal_or_user_api_access)])
def manual_tick(
    response_format: str = Query(
        "auto",
        alias="format",
        pattern="^(auto|text|json)$",
    ),
    group: str = Query("all", pattern="^(all|ingestion|maintenance)$"),
):
    return tick(response_format=response_format, group=group)


def tick(*, response_format: str = "auto", force_text: bool = False, group: str = "all"):
    ingestion_mode = "prod"
    tick_sources = [TICK_SOURCE] if group in ("all", "ingestion") else []

    logger.info(
        "tick_start",
        extra={
            "component": "runtime",
            "phase": "tick_start",
            "mode": ingestion_mode,
            "sources": tick_sources,
            "group": group,
        },
    )

    result = run_pipeline(group=group)

    payload = {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": tick_sources,
        **result,
    }

    render_mode = (response_format or "auto").strip().lower()
    if force_text:
        render_mode = "text"
    if render_mode == "text" or (render_mode == "auto" and should_use_text_logs()):
        return Response(
            content=format_tick_summary(payload),
            media_type="text/plain",
        )

    return payload
