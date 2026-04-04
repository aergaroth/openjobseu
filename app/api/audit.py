import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse

from app.domain.compliance.audit_filter_registry import get_audit_filter_registry
from storage.repositories.audit_repository import (
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_audit_source_filter_values,
    get_jobs_audit,
    get_failing_ats_integrations,
    get_source_compliance_trend,
    get_rejection_reasons_by_source,
)
from storage.repositories.ats_repository import (
    get_ats_integration_by_id,
    deactivate_ats_integration,
)
from storage.repositories.audit_companies_repository import get_audit_companies_list
from storage.db_engine import get_engine
from app.adapters.ats.registry import get_adapter

logger = logging.getLogger("openjobseu.runtime")

audit_ui_router = APIRouter(
    prefix="/audit",
    tags=["internal-audit-ui"],
    include_in_schema=False,  # Ukrywa widoki HTML w Swaggerze
)

audit_api_router = APIRouter(
    prefix="/audit",
    tags=["internal-audit"],
)

# Resolve path to project root (from app/api/audit.py -> root)
REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PANEL_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.html"
AUDIT_PANEL_JS_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.js"
AUDIT_PANEL_CSS_PATH = REPO_ROOT / "audit_tool" / "offer_audit_panel.css"


class AuditJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]
    counts: dict[str, Any]


class AuditCompaniesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class AuditStatsCompanyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_total_jobs: int
    items: list[dict[str, Any]]


class AuditStatsSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window: str
    items: list[dict[str, Any]]


class AuditSourceTrendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_days: int
    items: list[dict[str, Any]]


class AuditRejectionReasonsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_days: int
    items: list[dict[str, Any]]


class AtsHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days_threshold: int
    count: int
    items: list[dict[str, Any]]


class DeactivateAtsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    company_ats_id: str


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


@audit_ui_router.get("", response_class=HTMLResponse)
def audit_panel():
    try:
        content = _load_audit_panel_html()
    except OSError:
        logger.exception("failed to load audit panel html", extra={"path": str(AUDIT_PANEL_PATH)})
        raise HTTPException(status_code=500, detail="audit panel template not available")
    return HTMLResponse(content=content)


@audit_ui_router.get("/script.js")
def audit_panel_js():
    try:
        content = _load_audit_panel_js()
    except OSError:
        logger.exception("failed to load audit panel js", extra={"path": str(AUDIT_PANEL_JS_PATH)})
        raise HTTPException(status_code=500, detail="audit panel script not available")
    return Response(content=content, media_type="application/javascript")


@audit_ui_router.get("/style.css")
def audit_panel_css():
    try:
        content = _load_audit_panel_css()
    except OSError:
        logger.exception("failed to load audit panel css", extra={"path": str(AUDIT_PANEL_CSS_PATH)})
        raise HTTPException(status_code=500, detail="audit panel style not available")
    return Response(content=content, media_type="text/css")


@audit_api_router.get("/jobs", response_model=AuditJobsResponse)
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
    include_counts: bool = Query(True, description="Compute aggregate metrics"),
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
        include_counts=include_counts,
    )


@audit_api_router.get("/companies", response_model=AuditCompaniesResponse)
def audit_companies(
    q: str | None = Query(None, description="Fuzzy search across legal and brand names"),
    ats_provider: str | None = Query(None),
    is_active: bool | None = Query(None),
    min_score: int | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return get_audit_companies_list(
        q=q,
        ats_provider=ats_provider,
        is_active=is_active,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )


@audit_api_router.get("/filters", response_model=dict[str, list[str]])
def audit_filter_registry():
    payload = get_audit_filter_registry()
    payload["source"] = get_audit_source_filter_values()
    return payload


@audit_api_router.get("/stats/company", response_model=AuditStatsCompanyResponse)
def audit_company_stats(min_total_jobs: int = Query(10, ge=0, le=10000)):
    return {
        "min_total_jobs": int(min_total_jobs),
        "items": get_audit_company_compliance_stats(min_total_jobs=min_total_jobs),
    }


@audit_api_router.get("/stats/source-7d", response_model=AuditStatsSourceResponse)
def audit_source_stats_7d():
    return {
        "window": "last_7_days",
        "items": get_audit_source_compliance_stats_last_7d(),
    }


@audit_api_router.get("/stats/source-trend", response_model=AuditSourceTrendResponse)
def audit_source_trend(days: int = Query(30, ge=7, le=180)):
    return {"window_days": days, "items": get_source_compliance_trend(days=days)}


@audit_api_router.get("/stats/rejection-reasons", response_model=AuditRejectionReasonsResponse)
def audit_rejection_reasons(days: int = Query(30, ge=7, le=180)):
    return {"window_days": days, "items": get_rejection_reasons_by_source(days=days)}


@audit_api_router.get("/ats-health", response_model=AtsHealthResponse)
def audit_ats_health(days_threshold: int = Query(3, ge=1, le=30)):
    results = get_failing_ats_integrations(days_threshold=days_threshold)
    return {"days_threshold": days_threshold, "count": len(results), "items": results}


@audit_api_router.post("/ats-deactivate/{company_ats_id}", response_model=DeactivateAtsResponse)
def api_deactivate_ats(company_ats_id: str):
    with get_engine().begin() as conn:
        deactivate_ats_integration(conn, company_ats_id)
    return {"status": "ok", "company_ats_id": company_ats_id}


@audit_api_router.post("/ats-force-sync/{company_ats_id}")
def api_force_sync_ats(company_ats_id: str):
    with get_engine().connect() as conn:
        ats_integration = get_ats_integration_by_id(conn, company_ats_id)
        if not ats_integration:
            raise HTTPException(status_code=404, detail="ATS integration not found")

    provider = ats_integration["ats_provider"]
    try:
        adapter = get_adapter(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"No adapter found for provider: {provider}")

    company_dict = {
        "ats_slug": ats_integration["ats_slug"],
        "company_id": ats_integration["company_id"],
        "legal_name": ats_integration["legal_name"],
    }
    try:
        raw_jobs = adapter.fetch(company_dict, updated_since=None)
        return Response(
            content=f"Force sync successful. Fetched {len(raw_jobs)} jobs.",
            media_type="text/plain",
        )
    except Exception as e:
        logger.error(f"Force sync failed for {company_ats_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")


@audit_api_router.post("/tick-dev")
def run_tick_from_audit():
    # Lazy import to avoid circular dependency
    from app.api.system import tick

    result = tick(force_text=True)
    if isinstance(result, Response):
        return result
    if isinstance(result, str):
        return Response(content=result, media_type="text/plain")
    return result
