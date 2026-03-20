import logging
from fastapi import APIRouter, Depends, Query

from app.security.auth import require_internal_or_user_api_access
from storage.repositories.discovery_repository import (
    get_discovered_company_ats,
    get_discovery_candidates,
)
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.pipeline import run_discovery_pipeline
from app.workers.discovery.company_sources import run_company_source_discovery
from app.workers.discovery.ats_reverse import run_ats_reverse_discovery
from app.workers.discovery.dorking import run_dorking_discovery

logger = logging.getLogger("openjobseu.runtime")

discovery_router = APIRouter(
    prefix="/discovery",
    tags=["internal-discovery"],
    dependencies=[Depends(require_internal_or_user_api_access)],
)


@discovery_router.get("/audit")
def discovery_audit(q: str | None = Query(None, description="Fuzzy search across company names")):
    results = get_discovered_company_ats(q=q, limit=100)
    return {"count": len(results), "results": results}


@discovery_router.get("/candidates")
def discovery_candidates(q: str | None = Query(None, description="Fuzzy search across company names")):
    results = get_discovery_candidates(q=q, limit=50)
    return {"count": len(results), "results": results}


@discovery_router.post("/careers")
def run_careers():
    metrics = run_careers_discovery()
    return {"pipeline": "discovery", "phase": "careers_discovery", "metrics": metrics}


@discovery_router.post("/guess")
def run_guessing():
    metrics = run_ats_guessing()
    return {"pipeline": "discovery", "phase": "ats_guessing", "metrics": metrics}


@discovery_router.post("/ats-reverse")
def run_ats_reverse():
    metrics = run_ats_reverse_discovery()
    return {"pipeline": "discovery", "phase": "ats_reverse", "metrics": metrics}


@discovery_router.post("/dorking")
def run_dorking():
    metrics = run_dorking_discovery()
    return {"pipeline": "discovery", "phase": "dorking", "metrics": metrics}


@discovery_router.post("/run")
def run_discovery():
    return run_discovery_pipeline()


@discovery_router.post("/company-sources")
def run_company_sources():
    return run_company_source_discovery()