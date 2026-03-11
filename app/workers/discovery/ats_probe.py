import logging
from typing import Any, Dict

from app.adapters.ats.registry import get_adapter

logger = logging.getLogger("openjobseu.discovery")


def probe_ats(provider: str, slug: str) -> Dict[str, Any] | None:
    """Probe a registered ATS provider for job stats used by discovery workers."""

    normalized_provider = str(provider or "").strip()
    normalized_slug = str(slug or "").strip()

    try:
        adapter = get_adapter(normalized_provider)
    except ValueError as exc:
        logger.warning(
            "discovery probe skipped due to unsupported ats provider",
            extra={
                "component": "discovery",
                "phase": "probe",
                "provider": normalized_provider,
                "slug": normalized_slug,
                "error": str(exc),
            },
        )
        return None

    try:
        result = adapter.probe_jobs(slug)
    except NotImplementedError as exc:
        logger.warning(
            "discovery probe skipped because adapter probe is not implemented",
            extra={
                "component": "discovery",
                "phase": "probe",
                "provider": normalized_provider,
                "slug": normalized_slug,
                "error": str(exc),
            },
        )
        return None

    return result