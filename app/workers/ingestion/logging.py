import logging

logger = logging.getLogger("openjobseu")


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
        "ingestion event",
        extra={
            "component": "ingestion",
            "source": source,
            "phase": phase,
            **extra_fields,
        },
    )
