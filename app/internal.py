import os
import logging
from fastapi import APIRouter

from app.workers.tick import run_tick
from app.workers.ingestion.weworkremotely import run_weworkremotely_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.ingestion.remoteok import run_remoteok_ingestion

from app.workers.post_ingestion import run_post_ingestion


logger = logging.getLogger("openjobseu.runtime")

INGESTION_HANDLERS = {
    "weworkremotely": run_weworkremotely_ingestion,
    "remotive": run_remotive_ingestion,
    "remoteok": run_remoteok_ingestion,
}

router = APIRouter(prefix="/internal", tags=["internal"])

def get_available_ingestion_sources() -> list[str]:
    return list(INGESTION_HANDLERS.keys())


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

    actions = []

    if ingestion_mode == "local":
        result = run_tick()
        actions.extend(result.get("actions", []))
        return {
            "status": "ok",
            "mode": ingestion_mode,
            "sources": ["local"],
            "actions": actions,
        }

    for source in ingestion_sources:
        handler = INGESTION_HANDLERS.get(source)

        if not handler:
            logger.warning(
                "unknown ingestion source",
                extra={"source": source},
            )
            continue

        logger.info(
            "starting ingestion source",
            extra={"source": source},
        )

        try:
            result = handler()
            actions.extend(result.get("actions", []))
        except Exception as exc:
            logger.error(
                "ingestion source failed",
                extra={"source": source},
                exc_info=exc,
            )

    return {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": ingestion_sources,
        "actions": actions,
    }
