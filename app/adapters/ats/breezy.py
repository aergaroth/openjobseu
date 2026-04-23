import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import normalize_source_datetime, sanitize_url

logger = logging.getLogger(__name__)


class BreezyAdapter(ATSAdapter):
    """
    Breezy HR public JSON API — no authentication required.
    See: GET https://{subdomain}.breezy.hr/json
    """

    dorking_target = "breezy.hr"
    source_name = "breezy"
    active = True
    date_keys = ["published_date"]

    def _jobs_url(self, slug: str) -> str:
        return f"https://{slug}.breezy.hr/json"

    def fetch(self, company: Dict, updated_since: Any = None) -> list[dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for breezy company")
            return []

        resp = self.session.get(self._jobs_url(slug))
        resp.raise_for_status()
        data = self._parse_json(resp, slug, context="fetch")

        if not isinstance(data, list):
            raise ValueError(f"Breezy API did not return a list for {slug}")

        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if (item.get("state") or "").lower() != "published":
                continue
            item["_ats_slug"] = slug
            item["_incremental_at"] = item.get("published_date")
            rows.append(item)

        return self._filter_incremental_jobs(rows, updated_since, self.date_keys)

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning("Breezy normalize missing _ats_slug", extra={"raw_job_id": raw_job.get("_id")})
            return None

        job_id = str(raw_job.get("_id") or "").strip()
        if not job_id:
            return None

        title = (raw_job.get("name") or "").strip()
        if not title:
            return None

        source_url = sanitize_url(raw_job.get("url") or "") or ""
        if not source_url:
            source_url = f"https://{slug}.breezy.hr/p/{job_id}"

        location_obj = raw_job.get("location") or {}
        location = (location_obj.get("name") or "").strip()
        explicit_remote = bool(location_obj.get("is_remote"))

        tags = raw_job.get("tags") or []
        if isinstance(tags, list):
            tag_text = " ".join(str(t) for t in tags if t)
        else:
            tag_text = ""

        description_html = raw_job.get("description") or ""
        description = self.build_description(
            {"description": description_html},
            [("description", None)],
        )

        is_remote = self.detect_remote(
            title,
            location,
            explicit_flag=explicit_remote,
            extra_text=tag_text,
        )
        normalized_remote_scope = self.normalize_remote_scope(
            location if location else ("Remote" if explicit_remote else "")
        )

        dept_obj = raw_job.get("department") or {}
        department = (dept_obj.get("name") or "").strip() or None

        company_name = (
            self._extract_company_name_from_job(raw_job)
            or str(slug).replace("-", " ").replace("_", " ").strip().title()
        )
        first_seen_at = (
            normalize_source_datetime(raw_job.get("published_date")) or datetime.now(timezone.utc).isoformat()
        )
        salary_info = self.extract_salary(
            {
                "min": raw_job.get("salary_min"),
                "max": raw_job.get("salary_max"),
                "currency": raw_job.get("salary_currency"),
            }
        )

        return {
            "job_id": f"breezy:{slug}:{job_id}",
            "source": f"breezy:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": description.strip(),
            "remote_scope": normalized_remote_scope,
            "remote_source_flag": is_remote,
            "source_url": source_url,
            "status": "new",
            "department": department,
            "first_seen_at": first_seen_at,
            **salary_info,
        }

    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        if not str(slug or "").strip():
            return {}

        jobs = list(self.fetch(company={"ats_slug": slug}))
        if not jobs:
            return {}

        dates = [str(j["published_date"]) for j in jobs if isinstance(j, dict) and j.get("published_date")]
        recent_at = max(dates) if dates else None
        company_name = self._extract_company_name(jobs) or str(slug).replace("-", " ").replace("_", " ").strip().title()

        return {
            "jobs_total": len(jobs),
            "remote_hits": sum(1 for j in jobs if self._probe_job_remote(j)),
            "recent_job_at": recent_at,
            "company_name": company_name,
        }

    def _probe_job_remote(self, raw_job: dict) -> bool:
        location_obj = raw_job.get("location") or {}
        location = (location_obj.get("name") or "").strip()
        explicit_remote = bool(location_obj.get("is_remote"))
        tags = raw_job.get("tags") or []
        tag_text = " ".join(str(t) for t in tags if isinstance(tags, list) and t)
        return self.detect_remote(
            (raw_job.get("name") or "").strip(),
            location,
            explicit_flag=explicit_remote,
            extra_text=tag_text,
            is_probe=True,
        )

    @staticmethod
    def _extract_company_name_from_job(raw_job: dict) -> str:
        if not isinstance(raw_job, dict):
            return ""
        company = raw_job.get("company") or {}
        owner = raw_job.get("owner") or {}
        candidates = [
            raw_job.get("company_name"),
            company.get("name") if isinstance(company, dict) else None,
            owner.get("name") if isinstance(owner, dict) else None,
        ]
        for value in candidates:
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def _extract_company_name(self, jobs: list[dict]) -> str:
        for job in jobs:
            name = self._extract_company_name_from_job(job)
            if name:
                return name
        return ""


register(BreezyAdapter.source_name, BreezyAdapter)
