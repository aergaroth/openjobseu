import logging

logger = logging.getLogger("openjobseu.ingestion")


def log_ingestion(
    *,
    source: str,
    phase: str,
    **extra_fields,
) -> None:
    """
    Unified ingestion logger.

    phase examples:
    - fetch
    - ingestion_summary
    - error
    """

    payload = {
        "component": "ingestion",
        "source": source,
        "phase": phase,
        **extra_fields,
    }

    if phase == "fetch":
        logger.debug("ingestion", extra=payload)
        return

    logger.info("ingestion", extra=payload)
