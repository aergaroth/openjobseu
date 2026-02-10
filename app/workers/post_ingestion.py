# app/workers/post_ingestion.py

import logging

from app.workers.availability import run_availability_pipeline
from app.workers.lifecycle import run_lifecycle_pipeline
from storage.sqlite import init_db

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

    # Ensure DB schema exists even if ingestion phase had no valid sources.
    init_db()

    # --- Availability ---
    try:
        run_availability_pipeline()
    except Exception:
        logger.exception("availability step failed")

    # --- Lifecycle ---
    try:
        run_lifecycle_pipeline()
    except Exception:
        logger.exception("lifecycle step failed")

    logger.info("post-ingestion completed")
