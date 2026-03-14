import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
from app.workers.pipeline import run_pipeline
from storage.db_logic import (
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_audit_source_filter_values,
    get_jobs_audit,
)

from app.utils.backfill_compliance import backfill_missing_compliance_classes
from app.utils.backfill_salary import backfill_missing_salary_fields
from storage.repositories.discovery_repository import (
    get_discovered_company_ats,
    get_discovery_candidates,
)
from storage.db_engine import get_engine

from app.security.internal_access import require_internal_access

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PANEL_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.html"
TICK_SOURCE = "employer_ing"


@lru_cache(maxsize=1)
def _load_audit_panel_html() -> str:
    return AUDIT_PANEL_PATH.read_text(encoding="utf-8")


@router.get("/audit", response_class=HTMLResponse, dependencies=[Depends(require_user_login)])
def audit_panel():
    try:
        content = _load_audit_panel_html()
    except OSError:
        logger.exception("failed to load audit panel html", extra={"path": str(AUDIT_PANEL_PATH)})
        raise HTTPException(status_code=500, detail="audit panel template not available")

    return HTMLResponse(content=content)


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


@router.post("/discovery/run", dependencies=[Depends(require_internal_or_user_api_access)])
def run_discovery():
    return run_discovery_pipeline()


@router.post("/discovery/company-sources", dependencies=[Depends(require_internal_access)])
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


@router.post("/backfill-compliance", dependencies=[Depends(require_internal_access)])
def backfill_compliance(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_compliance_classes(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@router.post("/backfill-salary", dependencies=[Depends(require_internal_access)])
def backfill_salary(limit: int = Query(1000, ge=1, le=10000)):
    updated_count = backfill_missing_salary_fields(limit=limit)
    return {"status": "ok", "updated_jobs_count": updated_count}


@router.post("/tick", dependencies=[Depends(require_internal_or_user_api_access)])
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
