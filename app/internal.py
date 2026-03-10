import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse

from app.audit_filter_registry import get_audit_filter_registry
from app.logging import should_use_text_logs
from app.utils.tick_formatting import format_tick_summary
from app.workers.pipeline import run_pipeline
from storage.db_logic import (
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_audit_source_filter_values,
    get_jobs_audit,
)

from app.utils.backfill_compliance import backfill_missing_compliance_classes

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(prefix="/internal", tags=["internal"])

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PANEL_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.html"
TICK_SOURCE = "employer_ing"


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


@router.get("/audit/filters")
def audit_filter_registry():
    payload = get_audit_filter_registry()
    payload["source"] = get_audit_source_filter_values()
    return payload


@router.get("/audit/stats/company")
def audit_company_stats(
    min_total_jobs: int = Query(10, ge=0, le=10000),
):
    return {
        "min_total_jobs": int(min_total_jobs),
        "items": get_audit_company_compliance_stats(min_total_jobs=min_total_jobs),
    }


@router.get("/audit/stats/source-7d")
def audit_source_stats_7d():
    return {
        "window": "last_7_days",
        "items": get_audit_source_compliance_stats_last_7d(),
    }


@router.post("/audit/tick-dev")
def run_tick_from_audit():
    result = tick(force_text=True)
    if isinstance(result, Response):
        return result
    if isinstance(result, str):
        return Response(content=result, media_type="text/plain")
    return result


@router.post("/backfill-compliance")
def backfill_compliance(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_compliance_classes(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@router.post("/tick")
def manual_tick(
    response_format: str = Query(
        "auto",
        alias="format",
        pattern="^(auto|text|json)$",
    ),
):
    return tick(response_format=response_format)


def tick(*, response_format: str = "auto", force_text: bool = False):
    ingestion_mode = "prod"
    tick_sources = [TICK_SOURCE]

    logger.info(
        "tick_start",
        extra={
            "component": "runtime",
            "phase": "tick_start",
            "mode": ingestion_mode,
            "sources": tick_sources,
        },
    )

    result = run_pipeline()

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
