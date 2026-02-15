import os
import logging
from fastapi import APIRouter

import json

from app.workers.tick import run_tick
from app.workers.tick_pipeline import run_tick_pipeline

from app.workers.ingestion.weworkremotely import run_weworkremotely_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.ingestion.remoteok import run_remoteok_ingestion

from app.workers.ingestion.registry import (
    INGESTION_HANDLERS,
    get_available_ingestion_sources,
)

from fastapi import Response
from app.logging import should_use_text_logs

from app.utils.tick_formatting import format_tick_summary

logger = logging.getLogger("openjobseu.runtime")


router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
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
        return {
            "status": "ok",
            "mode": "local",
            "sources": ["local"],
            **result,
        }

    result = run_tick_pipeline(
        ingestion_sources=ingestion_sources,
        ingestion_handlers=INGESTION_HANDLERS,
    )

    payload = {
        "status": "ok",
        "mode": ingestion_mode,
        "sources": ingestion_sources,
        **result,
    }

    if should_use_text_logs():
        return Response(
            content=format_tick_summary(payload),
            media_type="text/plain",
        )

    return payload

