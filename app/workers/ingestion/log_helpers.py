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
    - start
    - fetch
    - end
    - error
    """

    logger.info(
        "ingestion",
        extra={
            "component": "ingestion",
            "source": source,
            "phase": phase,
            **extra_fields,
        },
    )
