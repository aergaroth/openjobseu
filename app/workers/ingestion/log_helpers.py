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

    if phase == "ingestion_summary":
        remote_model_counts = extra_fields.get("remote_model_counts") or {}
        payload.update(
            {
                "remote_only": remote_model_counts.get("remote_only", 0),
                "remote_non_remote": remote_model_counts.get("non_remote", 0),
                "remote_geo_restricted": remote_model_counts.get(
                    "remote_but_geo_restricted", 0
                ),
                "remote_unknown": remote_model_counts.get("unknown", 0),
            }
        )

    if phase == "fetch":
        logger.debug("ingestion", extra=payload)
        return

    logger.info(f"ingestion_summary[{source}]", extra=payload)
