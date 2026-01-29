import os
from fastapi import APIRouter
import logging

from app.workers.tick import run_tick, run_rss_tick

INGESTION_MODE = os.getenv("INGESTION_MODE", "rss")

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    if INGESTION_MODE =="local":
        result = run_tick()
    else
        result = run_rss_tick()

    logger.info("scheduler tick received")

    return {
        "status": "ok",
        "message": "scheduler tick received",
        **result
    }
