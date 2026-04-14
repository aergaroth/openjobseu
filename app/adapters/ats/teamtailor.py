from datetime import datetime, timezone
from typing import Any, Dict
import logging
from urllib.parse import urlparse

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import normalize_source_datetime, sanitize_url, to_utc_datetime

logger = logging.getLogger(__name__)


class TeamtailorAdapter(ATSAdapter):
    source_name = "teamtailor"
    active = True
    # Teamtailor uses API tokens per company — subdomains from search results cannot
    # be used as API tokens, so dorking would yield unusable slugs.
    dorking_target = None

    BASE_URL = "https://api.teamtailor.com/v1"
    API_VERSION_HEADER = "20161108"
    PAGE_SIZE = 30

    @staticmethod
    def _auth_headers(api_token: str) -> dict:
        return {
            "Authorization": f"Token token={api_token}",
            "X-Api-Version": TeamtailorAdapter.API_VERSION_HEADER,
        }

    @staticmethod
    def _resolve_token(company: dict) -> str:
        token = str(company.get("ats_slug") or "").strip()
        if not token:
            raise ValueError("ats_slug cannot be empty for teamtailor adapter")
        return token

    @staticmethod
    def _build_included_lookups(included: Any) -> dict:
        """Build a (type, id) → object lookup dict from JSON:API included array."""
        if not isinstance(included, list):
            return {}
        result = {}
        for item in included:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            item_id = str(item.get("id") or "")
            if item_type and item_id:
                result[(item_type, item_id)] = item
        return result

    def fetch(self, company: Dict, updated_since: Any = None) -> list[dict]:
        token = self._resolve_token(company)
        auth_headers = self._auth_headers(token)
        all_jobs: list[dict] = []
        page = 1

        while True:
            params = {
                "include": "locations,department",
                "filter[status]": "published",
                "page[size]": self.PAGE_SIZE,
                "page[number]": page,
            }
            resp = self.session.get(
                f"{self.BASE_URL}/jobs",
                params=params,
                headers=auth_headers,
            )
            resp.raise_for_status()
            data = self._parse_json(resp, token, context=f"page {page}")

            job_items = data.get("data", [])
            if not isinstance(job_items, list):
                raise ValueError("Teamtailor API did not return a data list")

            included = self._build_included_lookups(data.get("included") or [])

            for job in job_items:
                if not isinstance(job, dict):
                    continue
                job["_ats_slug"] = token
                job["_included"] = included
                job["_updated_at_flat"] = (job.get("attributes") or {}).get("updated-at")

            all_jobs.extend(j for j in job_items if isinstance(j, dict))

            total_pages = (data.get("meta") or {}).get("total-pages", 1)
            if page >= total_pages or not job_items:
                break
            page += 1

        return self._filter_incremental_jobs(all_jobs, updated_since, ["_updated_at_flat"])

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            raise ValueError("Missing _ats_slug in raw_job. Ensure fetch() was called.")

        included: dict = raw_job.get("_included") or {}
        job_id = raw_job.get("id")
        attrs: dict = raw_job.get("attributes") or {}
        links: dict = raw_job.get("links") or {}

        title = (attrs.get("title") or "").strip()
        source_url = sanitize_url(links.get("careersite-job-url") or "")

        if not job_id or not title or not source_url:
            return None

        # --- Department ---
        relationships: dict = raw_job.get("relationships") or {}
        dept_rel = (relationships.get("department") or {}).get("data") or {}
        dept_id = str(dept_rel.get("id") or "") if isinstance(dept_rel, dict) else ""
        dept_obj = included.get(("departments", dept_id)) if dept_id else None
        department = ((dept_obj or {}).get("attributes") or {}).get("name") or None

        # --- Locations ---
        loc_rels = (relationships.get("locations") or {}).get("data") or []
        location_parts = []
        for loc_ref in loc_rels:
            if not isinstance(loc_ref, dict):
                continue
            loc_id = str(loc_ref.get("id") or "")
            loc_obj = included.get(("locations", loc_id))
            if not loc_obj:
                continue
            loc_attrs = loc_obj.get("attributes") or {}
            parts = [p for p in [loc_attrs.get("city"), loc_attrs.get("country")] if p]
            if parts:
                location_parts.append(", ".join(parts))
        location_str = "; ".join(location_parts) or None

        # --- Remote scope ---
        remote_status = (attrs.get("remote-status") or "none").lower()
        if remote_status == "full":
            scope_input = f"{location_str}; Remote" if location_str else "Remote"
            explicit_remote = True
        elif remote_status == "hybrid":
            scope_input = f"{location_str}; hybrid" if location_str else "hybrid"
            explicit_remote = False
        else:
            scope_input = location_str
            explicit_remote = False

        is_remote = self.detect_remote(
            title,
            location_str,
            explicit_flag=explicit_remote,
            extra_text=attrs.get("body") or "",
        )
        remote_scope = self.normalize_remote_scope(scope_input)

        # --- Salary ---
        salary_dict = None
        if attrs.get("salary-min") is not None or attrs.get("salary-max") is not None:
            salary_dict = {
                "min": attrs.get("salary-min"),
                "max": attrs.get("salary-max"),
                "currency": attrs.get("salary-currency"),
                "period": attrs.get("salary-time-unit"),
            }
        salary_info = self.extract_salary(salary_dict)

        # --- Dates ---
        first_seen_at = normalize_source_datetime(attrs.get("created-at")) or datetime.now(timezone.utc).isoformat()

        company_name = (
            self._extract_company_name_from_job(raw_job) or slug.replace("-", " ").replace("_", " ").strip().title()
        )

        return {
            "job_id": f"teamtailor:{slug}:{job_id}",
            "source": f"teamtailor:{slug}",
            "source_job_id": str(job_id),
            "source_url": source_url,
            "title": title,
            "company_name": company_name,
            "description": (attrs.get("body") or "").strip(),
            "remote_source_flag": is_remote,
            "remote_scope": remote_scope,
            "department": department,
            "status": "new",
            "first_seen_at": first_seen_at,
            **salary_info,
        }

    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        token = str(slug or "").strip()
        if not token:
            raise ValueError("slug cannot be empty for teamtailor probe")

        auth_headers = self._auth_headers(token)
        params = {
            "include": "locations",
            "filter[status]": "published",
            "page[size]": self.PAGE_SIZE,
            "page[number]": 1,
        }
        resp = self.session.get(
            f"{self.BASE_URL}/jobs",
            params=params,
            headers=auth_headers,
        )
        resp.raise_for_status()
        data = self._parse_json(resp, token, context="probe")

        job_items = data.get("data", [])
        if not isinstance(job_items, list):
            raise ValueError("Teamtailor probe API did not return a data list")

        included = self._build_included_lookups(data.get("included") or [])
        jobs_total: int = (data.get("meta") or {}).get("record-count", len(job_items))
        remote_hits = 0
        recent_job_at: datetime | None = None
        company_name = (
            self._extract_company_name(job_items, included) or token.replace("-", " ").replace("_", " ").strip().title()
        )

        for job in job_items:
            if not isinstance(job, dict):
                continue
            attrs = job.get("attributes") or {}
            title = (attrs.get("title") or "").lower()
            remote_status = (attrs.get("remote-status") or "none").lower()
            explicit_remote = remote_status == "full"

            loc_rels = ((job.get("relationships") or {}).get("locations") or {}).get("data") or []
            loc_parts = []
            for loc_ref in loc_rels:
                if not isinstance(loc_ref, dict):
                    continue
                loc_id = str(loc_ref.get("id") or "")
                loc_obj = included.get(("locations", loc_id))
                if loc_obj:
                    loc_attrs = loc_obj.get("attributes") or {}
                    parts = [p for p in [loc_attrs.get("city"), loc_attrs.get("country")] if p]
                    if parts:
                        loc_parts.append(", ".join(parts))
            location_str = "; ".join(loc_parts) or None

            updated_raw = attrs.get("updated-at") or attrs.get("created-at")
            job_dt = to_utc_datetime(updated_raw)
            if job_dt and (recent_job_at is None or job_dt > recent_job_at):
                recent_job_at = job_dt

            if self.detect_remote(title, location_str, explicit_flag=explicit_remote, is_probe=True):
                remote_hits += 1

        return {
            "jobs_total": jobs_total,
            "recent_job_at": recent_job_at,
            "remote_hits": remote_hits,
            "company_name": company_name,
        }

    @staticmethod
    def _company_from_link(url: str | None) -> str:
        parsed = urlparse(str(url or "").strip())
        host = (parsed.hostname or "").strip().lower()
        if not host:
            return ""
        parts = [part for part in host.split(".") if part and part not in {"www", "jobs", "careers", "career"}]
        if not parts:
            return ""
        return parts[0].replace("-", " ").replace("_", " ").strip().title()

    @classmethod
    def _extract_company_name_from_job(cls, raw_job: dict) -> str:
        if not isinstance(raw_job, dict):
            return ""
        attrs = raw_job.get("attributes") or {}
        links = raw_job.get("links") or {}
        candidates = [
            attrs.get("company-name") if isinstance(attrs, dict) else None,
            attrs.get("company") if isinstance(attrs, dict) else None,
            cls._company_from_link(links.get("careersite-company-url") if isinstance(links, dict) else None),
        ]
        for value in candidates:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    @classmethod
    def _extract_company_name(cls, jobs: list[dict], included: dict) -> str:
        for job in jobs:
            name = cls._extract_company_name_from_job(job)
            if name:
                return name
        for item in (included or {}).values():
            if not isinstance(item, dict):
                continue
            attrs = item.get("attributes") or {}
            for key in ("name", "company-name", "company"):
                candidate = str(attrs.get(key) or "").strip()
                if candidate:
                    return candidate
        return ""


register(TeamtailorAdapter.source_name, TeamtailorAdapter)
