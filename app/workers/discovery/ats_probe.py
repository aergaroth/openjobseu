import logging
from typing import Any, Dict

import requests

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
    except requests.RequestException as exc:
        # 404s and network errors are expected during blind probing/guessing
        logger.debug(
            "discovery probe request failed",
            extra={
                "component": "discovery",
                "phase": "probe",
                "provider": normalized_provider,
                "slug": normalized_slug,
            },
        )
        return None
    except Exception as exc:
        logger.warning(
            "discovery probe unexpected error",
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