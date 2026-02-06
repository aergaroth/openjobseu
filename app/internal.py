import os
import logging
from fastapi import APIRouter

from app.workers.tick import run_tick
from app.workers.ingestion.rss import run_rss_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.post_ingestion import run_post_ingestion

logger = logging.getLogger("openjobseu.runtime")

INGESTION_HANDLERS = {
    "rss": run_rss_ingestion,
    "remotive": run_remotive_ingestion,
}

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    ingestion_mode = os.getenv("INGESTION_MODE", "prod")
    ingestion_sources = os.getenv("INGESTION_SOURCES", "rss").split(",")

    actions = []

    logger.info(
        "tick dispatcher invoked",
        extra={"mode": ingestion_mode, "sources": ingestion_sources},
    )

    if ingestion_mode == "local":
        result = run_tick()
        actions.extend(result.get("actions", []))
    else:
        for source in ingestion_sources:
            source = source.strip()
            handler = INGESTION_HANDLERS.get(source)

            if not handler:
                logger.warning("unknown ingestion source", extra={"source": source})
                continue

            logger.info("starting ingestion source", extra={"source": source})

            try:
                result = handler()
                actions.extend(result.get("actions", []))
            except Exception as exc:
                actions.append(f"{source}_failed")
                logger.error(
                    "ingestion source failed",
                    extra={"source": source},
                    exc_info=exc,
                )

        run_post_ingestion(actions)

    return {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": ingestion_sources,
        "actions": actions,
    }
