import os
import logging
from fastapi import APIRouter

from app.workers.tick import (
    run_tick,
    run_rss_tick,
    run_remotive_tick,
)

logger = logging.getLogger("openjobseu.runtime")

INGESTION_MODE = os.getenv("INGESTION_MODE", "prod")
INGESTION_SOURCES = os.getenv("INGESTION_SOURCES", "rss").split(",")

INGESTION_HANDLERS = {
    "rss": run_rss_tick,
    "remotive": run_remotive_tick,
}

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    ingestion_mode = os.getenv("INGESTION_MODE", "prod")
    ingestion_sources = os.getenv("INGESTION_SOURCES", "rss").split(",")

    logger.info(
        "tick dispatcher invoked",
        extra={
            "mode": ingestion_mode,
            "sources": ingestion_sources,
        },
    )

    actions = []

    if INGESTION_MODE == "local":
        result = run_tick()
        actions.extend(result.get("actions", []))

    else:
        for source in INGESTION_SOURCES:
            source = source.strip()
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

    logger.info(
        "scheduler tick received",
        extra={
            "mode": INGESTION_MODE,
            "sources": INGESTION_SOURCES,
            "actions": actions,
        },
    )

    return {
        "status": "ok",
        "mode": INGESTION_MODE,
        "sources": INGESTION_SOURCES,
        "actions": actions,
    }
