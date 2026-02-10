import logging
from typing import Iterable, Dict, Callable, List

from app.workers.post_ingestion import run_post_ingestion

logger = logging.getLogger("openjobseu.pipeline")


def run_tick_pipeline(
    *,
    ingestion_sources: Iterable[str],
    ingestion_handlers: Dict[str, Callable[[], dict]],
) -> dict:
    """
    Execute full tick pipeline:
    ingestion → post_ingestion
    """

    actions: List[str] = []

    logger.info(
        "tick pipeline started",
        extra={"sources": list(ingestion_sources)},
    )

    # --- Ingestion phase ---
    for source in ingestion_sources:
        handler = ingestion_handlers.get(source)

        if not handler:
            logger.warning("unknown ingestion source", extra={"source": source})
            continue

        logger.info("starting ingestion source", extra={"source": source})

        try:
            result = handler()
            actions.extend(result.get("actions", []))
        except Exception:
            logger.exception("ingestion source failed", extra={"source": source})

    # --- Post-ingestion (availability + lifecycle) ---
    run_post_ingestion()

    logger.info(
        "tick pipeline finished",
        extra={"actions": actions},
    )

    return {
        "actions": actions,
    }
