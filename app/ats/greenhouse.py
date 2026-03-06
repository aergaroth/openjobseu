from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from app.ats.base import BaseATSAdapter
from app.ats.registry import register
from app.utils.cleaning import clean_description

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}


def _sanitize_url(raw_url: Any) -> str | None:
    if not isinstance(raw_url, str):
        return None

    value = raw_url.strip()
    if not value:
        return None

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value

    filtered_query = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_QUERY_PARAMS:
            continue
        filtered_query.append((key, val))

    clean_query = urlencode(filtered_query, doseq=True)
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, clean_query, "")
    )


def _sanitize_location(raw_location: Any) -> str | None:
    if not isinstance(raw_location, str):
        return None
    cleaned = " ".join(raw_location.split())
    return cleaned or None


def _parse_datetime_string(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None


def _normalize_source_datetime(raw_value: Any) -> str | None:
    if raw_value in (None, ""):
        return None

    dt: datetime | None = None

    if isinstance(raw_value, datetime):
        dt = raw_value
    elif isinstance(raw_value, struct_time):
        dt = datetime(*raw_value[:6], tzinfo=timezone.utc)
    elif isinstance(raw_value, (tuple, list)) and len(raw_value) >= 6:
        dt = datetime(*raw_value[:6], tzinfo=timezone.utc)
    elif isinstance(raw_value, (int, float)):
        dt = datetime.fromtimestamp(raw_value, tz=timezone.utc)
    elif isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return None
        dt = _parse_datetime_string(value)
        if dt is None:
            return None

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat()


def _to_utc_datetime(raw_value: Any) -> datetime | None:
    normalized = _normalize_source_datetime(raw_value)
    if not normalized:
        return None
    return datetime.fromisoformat(normalized)


class GreenhouseAdapter(BaseATSAdapter):
    provider = "greenhouse"
    active = True
    API_URL_TEMPLATE = (
        "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    )

    def __init__(self):
        self._board_token: str | None = None

    @staticmethod
    def _resolve_board_token(company: dict) -> str:
        token = str(company.get("ats_slug") or "").strip()
        if not token:
            raise ValueError("ats_slug cannot be empty for greenhouse adapter")
        return token

    @staticmethod
    def _fallback_company_name(board_token: str) -> str:
        return board_token.replace("-", " ").replace("_", " ").strip() or "unknown"

    def fetch(self, company: dict, updated_since: Any = None) -> list[dict]:
        board_token = self._resolve_board_token(company)
        self._board_token = board_token
        api_url = self.API_URL_TEMPLATE.format(board_token=board_token)

        resp = requests.get(
            api_url,
            headers={
                "User-Agent": "OpenJobsEU/1.0 (https://openjobseu.org)",
                "Accept": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()

        if isinstance(payload, list):
            jobs = payload
            return self._filter_incremental_jobs(jobs, updated_since)
        if not isinstance(payload, dict):
            raise ValueError("Greenhouse API did not return a dict payload")

        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            raise ValueError("Greenhouse API payload does not contain a jobs list")

        return self._filter_incremental_jobs(jobs, updated_since)

    @staticmethod
    def _filter_incremental_jobs(jobs: list[dict], updated_since: Any) -> list[dict]:
        if updated_since in (None, ""):
            return jobs

        cutoff = _to_utc_datetime(updated_since)
        if cutoff is None:
            return jobs

        filtered_jobs: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                filtered_jobs.append(job)
                continue

            source_updated_at = _to_utc_datetime(job.get("updated_at"))
            if source_updated_at is None:
                source_updated_at = _to_utc_datetime(job.get("pubDate"))

            if source_updated_at is None or source_updated_at >= cutoff:
                filtered_jobs.append(job)

        return filtered_jobs

    def normalize(self, raw_job: dict) -> dict | None:
        board_token = self._board_token
        if not board_token:
            raise ValueError("fetch(company) must be called before normalize(raw_job)")
        raw_id = raw_job.get("id")
        title = (raw_job.get("title") or "").strip()
        source_url = _sanitize_url(raw_job.get("absolute_url"))

        location = None
        raw_location = raw_job.get("location")
        if isinstance(raw_location, dict):
            location = _sanitize_location(raw_location.get("name"))
        elif isinstance(raw_location, str):
            location = _sanitize_location(raw_location)

        updated_at = _normalize_source_datetime(raw_job.get("updated_at"))
        pub_date = _normalize_source_datetime(raw_job.get("pubDate"))
        first_seen_at = updated_at or pub_date or datetime.now(timezone.utc).isoformat()

        company_name = (
            (raw_job.get("company_name") or "").strip()
            or (raw_job.get("company") or "").strip()
            or self._fallback_company_name(board_token)
        )

        description = raw_job.get("content") or raw_job.get("description") or ""
        if not isinstance(description, str):
            description = str(description)

        if not raw_id or not title or not source_url:
            return None

        cleaned_description = clean_description(description, source=self.provider)
        full_text = f"{title} {cleaned_description} {location or ''}".lower()
        remote_keywords = [
            "remote",
            "home based",
            "work from home",
            "fully remote",
        ]
        is_remote = any(kw in full_text for kw in remote_keywords)

        return {
            "job_id": f"greenhouse:{board_token}:{raw_id}",
            "source": f"greenhouse:{board_token}",
            "source_job_id": str(raw_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": cleaned_description.strip(),
            "remote_source_flag": is_remote,
            "remote_scope": location,
            "status": "new",
            "first_seen_at": first_seen_at,
        }


register(GreenhouseAdapter.provider, GreenhouseAdapter)
