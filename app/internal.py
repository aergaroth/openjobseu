import os
import logging
from fastapi import APIRouter

from app.workers.tick import run_tick
from app.workers.tick_pipeline import run_tick_pipeline

from app.workers.ingestion.weworkremotely import run_weworkremotely_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.ingestion.remoteok import run_remoteok_ingestion

logger = logging.getLogger("openjobseu.runtime")

INGESTION_HANDLERS = {
    "weworkremotely": run_weworkremotely_ingestion,
    "remotive": run_remotive_ingestion,
    "remoteok": run_remoteok_ingestion,
}

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    ingestion_mode = os.getenv("INGESTION_MODE", "prod")

    raw_sources = os.getenv("INGESTION_SOURCES")
    if raw_sources:
        ingestion_sources = [s.strip() for s in raw_sources.split(",")]
    else:
        ingestion_sources = list(INGESTION_HANDLERS.keys())

    logger.info(
        "tick dispatcher invoked",
        extra={
            "mode": ingestion_mode,
            "sources": ingestion_sources,
        },
    )

    if ingestion_mode == "local":
        result = run_tick()
        return {
            "status": "ok",
            "mode": "local",
            "sources": ["local"],
            "actions": result.get("actions", []),
        }

    result = run_tick_pipeline(
        ingestion_sources=ingestion_sources,
        ingestion_handlers=INGESTION_HANDLERS,
    )

    return {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": ingestion_sources,
        **result,
    }
