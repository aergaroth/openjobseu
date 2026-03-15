import logging
from typing import Any, Dict, List, Tuple

import requests

from app.adapters.ats.base import ATSAdapter

logger = logging.getLogger("openjobseu.ingestion.employer")


def fetch_company_jobs(
    company: Dict, adapter: ATSAdapter, updated_since: Any = None
) -> Tuple[List[Dict] | None, str | None]:
    """
    Fetch raw jobs from an ATS for a given company.

    Returns:
        A tuple of (raw_jobs_list, error_string).
        If successful, error_string is None.
        If fails, raw_jobs_list is None.
    """
    provider = str(company.get("ats_provider") or "").strip().lower()
    try:
        raw_jobs = list(adapter.fetch(company, updated_since=updated_since))
        return raw_jobs, None
    except requests.HTTPError as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "employer ingestion fetch failed with http status",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "status_code": status_code,
            },
        )
        error = "invalid_ats_slug" if status_code == 404 else "fetch_failed"
        return None, error
    except (requests.ConnectionError, requests.Timeout) as exc:
        logger.warning(
            "employer ingestion fetch failed due to network error",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
            },
        )
        return None, "fetch_network_failed"
    except requests.RequestException as exc:
        logger.warning(
            "employer ingestion fetch failed due to request exception",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
            },
        )
        return None, "fetch_failed"
    except Exception as exc:
        logger.error(
            "employer ingestion fetch failed with unhandled exception",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
        return None, "fetch_failed"