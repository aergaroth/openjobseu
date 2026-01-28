from fastapi import APIRouter
import logging

logger = logging.getLogger("openjobseu.runtime")

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    logger.info("scheduler tick received")
    return {
        "status": "ok",
        "message": "scheduler tick received"
    }
