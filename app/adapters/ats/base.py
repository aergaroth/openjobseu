from abc import ABC, abstractmethod
from typing import Any, Iterable, Dict
import os
import re
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import JSONDecodeError

from app.adapters.ats.utils import to_utc_datetime
from app.utils.cleaning import normalize_remote_scope as _normalize_remote_scope

logger = logging.getLogger(__name__)


class TimeoutSession(requests.Session):
    """
    Custom requests.Session that enforces a default timeout on all HTTP requests
    and provides automatic retries for transient network/server errors.
    """

    def __init__(self, timeout: int = 30, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

        # W środowisku testowym wyłączamy retries, żeby uniknąć sztucznego usypiania testów na mockowanych błędach (7s/test)
        is_testing = "PYTEST_CURRENT_TEST" in os.environ

        # Configure automatic retries for 429 (Rate Limit) and 5xx (Server Errors)
        retry_strategy = Retry(
            total=0 if is_testing else 3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().request(method, url, **kwargs)


class ATSAdapter(ABC):
    dorking_target: str | None = None

    """
    Abstract base class for ATS adapters.
    
    Each adapter must implement:
    - source_name: unique identifier for the ATS provider
    - fetch(company, updated_since): fetch raw jobs from ATS API
    - normalize(raw_job): convert raw ATS payload to canonical job dict
  
    The normalize method should return a dict with at least the following fields:
    - source: str (e.g. "greenhouse:acme")
    - source_job_id: str (unique ID from ATS)
    - title: str
    - description: str
    - remote_scope: str
    - company_name: str (optional)
    Adapters can also implement provider-specific logic for handling API requests, pagination, rate limits, etc.
       
    """
    REMOTE_KEYWORDS_NORMALIZE = [
        "remote job",
        "home based",
        "work from home",
        "fully remote",
    ]
    REMOTE_KEYWORDS_PROBE = [
        "remote",
        "anywhere",
        "distributed",
        "work from home",
    ]

    def __init__(self):
        self.session = TimeoutSession(timeout=30)
        self.session.headers.update(
            {
                "User-Agent": "OpenJobsEU/1.0 (https://openjobseu.org)",
                "Accept": "application/json",
            }
        )

    source_name: str

    # Backward compatibility: allow access via 'provider' attribute
    @property
    def provider(self) -> str:
        """Alias for source_name (backward compatibility)."""
        return self.source_name

    def normalize_remote_scope(self, value: str | None) -> str:
        """
        Normalize remote/location strings across ATS providers.
        """
        return _normalize_remote_scope(value)

    def _parse_json(
        self,
        response: requests.Response,
        slug: str,
        context: str = "",
        extra_log_fields: dict | None = None,
    ) -> Any:
        """
        Safely parse JSON from a response, logging and raising a uniform error on failure.
        """
        try:
            return response.json()
        except JSONDecodeError as e:
            raw_text = response.text[:500]
            provider = self.source_name.title()
            msg = f"Failed to decode JSON from {provider} ATS"
            if context:
                msg += f" {context}"

            log_extra = {
                "ats_slug": slug,
                "http_status": response.status_code,
                "response_text": raw_text,
            }
            if extra_log_fields:
                log_extra.update(extra_log_fields)

            logger.error(msg, extra=log_extra)

            err_msg = f"{provider} API returned non-JSON response for {slug}"
            if context:
                err_msg += f" ({context})"
            raise ValueError(err_msg) from e

    def extract_salary(self, salary_dict: dict | None) -> dict:
        """
        Generic helper to extract and normalize salary information from ATS-specific dictionary structures.
        """
        result = {
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "salary_period": None,
            "salary_source": None,
        }
        if not isinstance(salary_dict, dict):
            return result

        def get_first_valid(keys: list) -> Any:
            for k in keys:
                if salary_dict.get(k) is not None:
                    return salary_dict[k]
            return None

        try:
            s_min = get_first_valid(["minAmount", "min_value", "min"])
            s_max = get_first_valid(["maxAmount", "max_value", "max"])

            if s_min is not None:
                result["salary_min"] = int(float(s_min))
            if s_max is not None:
                result["salary_max"] = int(float(s_max))

            curr = get_first_valid(["currencyCode", "currency"])
            if isinstance(curr, str) and curr.strip():
                result["salary_currency"] = curr.strip().upper()

            interval = str(get_first_valid(["interval", "period", "unit", "type"]) or "").lower()
            if "year" in interval or "annu" in interval:
                result["salary_period"] = "yearly"
            elif "month" in interval:
                result["salary_period"] = "monthly"
            elif "hour" in interval:
                result["salary_period"] = "hourly"

            if result["salary_min"] is not None or result["salary_max"] is not None:
                result["salary_source"] = "ats_api"
        except (ValueError, TypeError):
            pass

        return result

    def _filter_incremental_jobs(self, jobs: list[dict], updated_since: Any, date_keys: list[str]) -> list[dict]:
        if updated_since in (None, ""):
            return jobs

        cutoff = to_utc_datetime(updated_since)
        if cutoff is None:
            return jobs

        filtered_jobs: list[dict] = []
        for job in jobs:
            if not isinstance(job, dict):
                filtered_jobs.append(job)
                continue

            source_updated_at = None
            for key in date_keys:
                val = job.get(key)
                if val:
                    source_updated_at = to_utc_datetime(val)
                    if source_updated_at is not None:
                        break

            if source_updated_at is None or source_updated_at >= cutoff:
                filtered_jobs.append(job)

        return filtered_jobs

    def build_description(self, raw_job: dict, mapping: list[tuple[Any, Any]]) -> str:
        """
        Assembles a job description from multiple fields in a raw ATS payload.
        `mapping` is a list of tuples: `(field_keys, heading)`
        - `field_keys`: a string or list of strings (checked in order as fallbacks).
        - `heading`: an optional string to use as an HTML <h3> heading.
        """
        desc_parts = []
        for keys, heading in mapping:
            if isinstance(keys, str):
                keys = [keys]

            val = None
            for k in keys:
                v = raw_job.get(k)
                if v and str(v).strip():
                    val = str(v).strip()
                    break

            if val:
                if heading:
                    desc_parts.append(f"<h3>{heading}</h3>\n{val}")
                else:
                    desc_parts.append(val)

        return "\n\n".join(desc_parts)

    def detect_remote(
        self,
        title: str | None,
        location: str | None,
        explicit_flag: bool = False,
        extra_text: str = "",
        is_probe: bool = False,
    ) -> bool:
        """
        Unified remote detection logic checking explicit flags and keywords
        in title, location, and optional extra text using word boundaries.
        """
        if explicit_flag:
            return True

        full_text = f"{title or ''} {location or ''} {extra_text}"
        keywords = self.REMOTE_KEYWORDS_PROBE if is_probe else self.REMOTE_KEYWORDS_NORMALIZE

        # Budujemy wyrażenie regularne szukające całych słów/fraz (np. \b(?:remote|work from home)\b)
        pattern = r"\b(?:" + "|".join(map(re.escape, keywords)) + r")\b"
        return bool(re.search(pattern, full_text, flags=re.IGNORECASE))

    @abstractmethod
    def fetch(self, company: Dict, updated_since: Any = None) -> Iterable[Dict]:
        """
        Fetch raw jobs from ATS API.

        Args:
            company: Company dict with ats_slug and other metadata
            updated_since: Optional datetime for incremental fetching

        Returns:
            Iterable of raw ATS job payloads
        """
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_job: Dict) -> Dict | None:
        """
        Convert raw ATS payload to canonical job dict.

        Returns None if job should be skipped.

        Expected output fields:
        - source: str
        - source_job_id: str
        - title: str
        - description: str
        - remote_scope: str
        - company_name: str (optional)
        """
        raise NotImplementedError

    @abstractmethod
    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        """Lightweight discovery probe that inspects availability of jobs."""
        raise NotImplementedError


# Backward compatibility alias
BaseATSAdapter = ATSAdapter
