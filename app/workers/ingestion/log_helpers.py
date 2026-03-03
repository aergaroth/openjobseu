import logging

from app.domain.classification.enums import RemoteClass

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
                RemoteClass.REMOTE_ONLY.value: remote_model_counts.get(
                    RemoteClass.REMOTE_ONLY.value, 0
                ),
                "remote_non_remote": remote_model_counts.get(RemoteClass.NON_REMOTE.value, 0),
                "remote_geo_restricted": remote_model_counts.get(
                    "remote_but_geo_restricted", 0
                ),
                f"remote_{RemoteClass.UNKNOWN.value}": remote_model_counts.get(
                    RemoteClass.UNKNOWN.value, 0
                ),
            }
        )

    if phase == "fetch":
        logger.debug("ingestion", extra=payload)
        return

    logger.info(f"ingestion_summary[{source}]", extra=payload)
