# app/workers/post_ingestion.py

import logging
from time import perf_counter

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

    started = perf_counter()
    availability_summary = {
        "checked": 0,
        "expired": 0,
        "unreachable": 0,
    }

    # Ensure DB schema exists even if ingestion phase had no valid sources.
    init_db()

    # --- Availability ---
    try:
        result = run_availability_pipeline() or {}
        availability_summary["checked"] = int(result.get("checked", 0) or 0)
        availability_summary["expired"] = int(result.get("expired", 0) or 0)
        availability_summary["unreachable"] = int(result.get("unreachable", 0) or 0)
    except Exception:
        logger.exception("availability step failed")

    # --- Lifecycle ---
    try:
        run_lifecycle_pipeline()
    except Exception:
        logger.exception("lifecycle step failed")

    duration_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "post_ingestion",
        extra={
            "component": "post_ingestion",
            "phase": "post_ingestion_summary",
            "availability_checked": availability_summary["checked"],
            "expired": availability_summary["expired"],
            "unreachable": availability_summary["unreachable"],
            "duration_ms": duration_ms,
        },
    )
