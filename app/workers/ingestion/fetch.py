import logging
import time
from typing import Any, Dict, Iterable, Iterator, Tuple

import requests

from app.adapters.ats.base import ATSAdapter

logger = logging.getLogger("openjobseu.ingestion.employer")


class FetchCompanyJobsError(Exception):
    def __init__(self, error_code: str):
        super().__init__(error_code)
        self.error_code = error_code


def _map_fetch_exception(
    company: Dict,
    provider: str,
    start_time: float,
    exc: Exception,
) -> str:
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    if isinstance(exc, requests.HTTPError):
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "employer ingestion fetch failed with http status",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        return "invalid_ats_slug" if status_code == 404 else "fetch_failed"

    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        logger.warning(
            "employer ingestion fetch failed due to network error",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
                "duration_ms": duration_ms,
            },
        )
        return "fetch_network_failed"

    if isinstance(exc, requests.RequestException):
        logger.warning(
            "employer ingestion fetch failed due to request exception",
            extra={
                "company_id": company.get("company_id"),
                "ats_provider": provider,
                "ats_slug": company.get("ats_slug"),
                "error_type": type(exc).__name__,
                "duration_ms": duration_ms,
            },
        )
        return "fetch_failed"

    logger.error(
        "employer ingestion fetch failed with unhandled exception",
        extra={
            "company_id": company.get("company_id"),
            "ats_provider": provider,
            "ats_slug": company.get("ats_slug"),
            "error": str(exc),
            "error_type": type(exc).__name__,
            "duration_ms": duration_ms,
        },
    )
    return "fetch_failed"


def fetch_company_jobs(
    company: Dict, adapter: ATSAdapter, updated_since: Any = None
) -> Tuple[Iterator[Dict] | None, str | None]:
    """
    Fetch raw jobs from an ATS for a given company.

    Returns:
        A tuple of (raw_jobs_iterator, error_string).
        If successful, error_string is None.
        If fails before iteration starts, raw_jobs_iterator is None.
    """
    provider = str(company.get("ats_provider") or "").strip().lower()
    start_time = time.perf_counter()

    try:
        raw_jobs: Iterable[Dict] = adapter.fetch(company, updated_since=updated_since)
        raw_jobs_iter = iter(raw_jobs)
    except Exception as exc:
        return None, _map_fetch_exception(company, provider, start_time, exc)

    def _stream_jobs() -> Iterator[Dict]:
        try:
            yield from raw_jobs_iter
        except Exception as exc:
            raise FetchCompanyJobsError(
                _map_fetch_exception(company, provider, start_time, exc)
            ) from exc

    return _stream_jobs(), None
