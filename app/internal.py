import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse

from app.logging import should_use_text_logs
from app.utils.tick_formatting import format_tick_summary
from app.workers.ingestion.registry import INGESTION_HANDLERS
from app.workers.tick import run_tick
from app.workers.tick_pipeline import run_tick_pipeline
from storage.sqlite import get_jobs_audit

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(prefix="/internal", tags=["internal"])

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PANEL_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.html"
TICK_DEV_SCRIPT_PATH = REPO_ROOT / "scripts" / "tick-dev.sh"


def _truncate_output(value: str, max_chars: int = 8000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


@lru_cache(maxsize=1)
def _load_audit_panel_html() -> str:
    return AUDIT_PANEL_PATH.read_text(encoding="utf-8")


@router.get("/audit", response_class=HTMLResponse)
def audit_panel():
    try:
        content = _load_audit_panel_html()
    except OSError:
        logger.exception("failed to load audit panel html", extra={"path": str(AUDIT_PANEL_PATH)})
        raise HTTPException(status_code=500, detail="audit panel template not available")

    return HTMLResponse(content=content)


@router.get("/audit/jobs")
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


@router.post("/audit/tick-dev")
def run_tick_dev_script():
    if not TICK_DEV_SCRIPT_PATH.exists():
        raise HTTPException(status_code=404, detail="scripts/tick-dev.sh not found")

    try:
        result = subprocess.run(
            ["bash", str(TICK_DEV_SCRIPT_PATH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "returncode": -1,
            "stdout": _truncate_output(str(exc.stdout or "")),
            "stderr": _truncate_output(str(exc.stderr or "")),
        }

    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": int(result.returncode),
        "stdout": _truncate_output(result.stdout or ""),
        "stderr": _truncate_output(result.stderr or ""),
    }


@router.post("/tick")
def manual_tick():
    return tick()


def tick():
    ingestion_mode = os.getenv("INGESTION_MODE", "prod")

    raw_sources = os.getenv("INGESTION_SOURCES")
    if raw_sources:
        ingestion_sources = [s.strip() for s in raw_sources.split(",")]
    else:
        ingestion_sources = list(INGESTION_HANDLERS.keys())

    tick_sources = ["local"] if ingestion_mode == "local" else ingestion_sources

    logger.info(
        "tick_start",
        extra={
            "component": "runtime",
            "phase": "tick_start",
            "mode": ingestion_mode,
            "sources": tick_sources,
        },
    )

    if ingestion_mode == "local":
        result = run_tick()
    else:
        result = run_tick_pipeline(
            ingestion_sources=ingestion_sources,
            ingestion_handlers=INGESTION_HANDLERS,
        )

    payload = {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": tick_sources,
        **result,
    }

    if should_use_text_logs():
        return Response(
            content=format_tick_summary(payload),
            media_type="text/plain",
        )

    return payload
