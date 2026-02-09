# app/workers/post_ingestion.py

import logging

from app.workers.availability import run_availability_checks
from app.workers.lifecycle import run_lifecycle_rules

logger = logging.getLogger("openjobseu.post_ingestion")


def run_post_ingestion() -> None:
    """
    Post-ingestion pipeline step.

    Executes:
    - availability checks
    - lifecycle transitions

    This function:
    - does NOT return anything
    - does NOT mutate ingestion actions
    - reports only via logs
    """

    logger.info("post-ingestion started")

    # --- Availability ---
    try:
        run_availability_checks()
    except Exception:
        logger.exception("availability step failed")

    # --- Lifecycle ---
    try:
        run_lifecycle_rules()
    except Exception:
        logger.exception("lifecycle step failed")

    logger.info("post-ingestion completed")
