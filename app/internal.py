from fastapi import APIRouter
import logging

from app.workers.tick import run_tick

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    result = run_tick()

    logger.info("scheduler tick received")

    return {
        "status": "ok",
        "message": "scheduler tick received"
        **result
    }
