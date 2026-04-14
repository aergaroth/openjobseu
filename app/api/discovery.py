import logging
from pydantic import BaseModel, ConfigDict
from typing import Any
from fastapi import APIRouter, Query

from storage.db_engine import get_engine
from storage.repositories.discovery_repository import (
    get_discovered_company_ats,
    get_discovery_candidates,
    get_discovered_slugs,
)
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.pipeline import run_discovery_pipeline
from app.workers.discovery.company_sources import run_company_source_discovery
from app.workers.discovery.ats_reverse import run_ats_reverse_discovery
from app.workers.discovery.dorking import run_dorking_discovery

logger = logging.getLogger("openjobseu.runtime")

discovery_ui_router = APIRouter(prefix="/discovery", tags=["internal-discovery-ui"])
discovery_ops_router = APIRouter(prefix="/discovery", tags=["internal-discovery-ops"])


class DiscoveryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int
    results: list[dict[str, Any]]


class DiscoveryPhaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: str
    phase: str
    metrics: dict[str, Any]


class DiscoveryRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    metrics: dict[str, Any]
    actions: list[str]


@discovery_ui_router.get("/audit", response_model=DiscoveryListResponse)
def discovery_audit(
    q: str | None = Query(None, description="Fuzzy search across company names"),
):
    results = get_discovered_company_ats(q=q, limit=100)
    return {"count": len(results), "results": results}


@discovery_ui_router.get("/candidates", response_model=DiscoveryListResponse)
def discovery_candidates(
    q: str | None = Query(None, description="Fuzzy search across company names"),
):
    results = get_discovery_candidates(q=q, limit=50)
    return {"count": len(results), "results": results}


@discovery_ui_router.get("/slug-candidates", response_model=DiscoveryListResponse)
def discovery_slug_candidates(
    provider: str | None = Query(None, description="Filter by ATS provider, e.g. teamtailor"),
    status: str | None = Query("needs_token", description="Filter by discovered slug status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of rows to return"),
):
    with get_engine().connect() as conn:
        results = get_discovered_slugs(conn, provider=provider, status=status, limit=limit)
    return {"count": len(results), "results": results}


@discovery_ops_router.post("/careers", response_model=DiscoveryPhaseResponse)
def run_careers():
    metrics = run_careers_discovery()
    return {"pipeline": "discovery", "phase": "careers_discovery", "metrics": metrics}


@discovery_ops_router.post("/guess", response_model=DiscoveryPhaseResponse)
def run_guessing():
    metrics = run_ats_guessing()
    return {"pipeline": "discovery", "phase": "ats_guessing", "metrics": metrics}


@discovery_ops_router.post("/ats-reverse", response_model=DiscoveryPhaseResponse)
def run_ats_reverse():
    metrics = run_ats_reverse_discovery()
    return {"pipeline": "discovery", "phase": "ats_reverse", "metrics": metrics}


@discovery_ops_router.post("/dorking", response_model=DiscoveryPhaseResponse)
def run_dorking():
    metrics = run_dorking_discovery()
    return {"pipeline": "discovery", "phase": "dorking", "metrics": metrics}


@discovery_ops_router.post("/run", response_model=DiscoveryRunResponse)
def run_discovery():
    return run_discovery_pipeline()


@discovery_ops_router.post("/company-sources", response_model=dict[str, Any])
def run_company_sources():
    return run_company_source_discovery()
