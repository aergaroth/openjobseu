import json
import logging
from typing import Any, Dict

from app.adapters.ats.base import ATSAdapter
from app.adapters.ats.registry import register
from app.adapters.ats.utils import sanitize_url

logger = logging.getLogger(__name__)


class TraffitAdapter(ATSAdapter):
    """
    Traffit public API — published job posts (no authentication).
    See: GET https://{subdomain}.traffit.com/public/job_posts/published
    """

    dorking_target = "traffit.com"
    source_name = "traffit"
    active = True
    PAGE_SIZE = 30

    def _published_url(self, slug: str) -> str:
        return f"https://{slug}.traffit.com/public/job_posts/published"

    @staticmethod
    def _header_int(headers: Any, *names: str) -> int | None:
        if not hasattr(headers, "get"):
            return None
        for name in names:
            v = headers.get(name)
            if v is None:
                v = headers.get(name.lower())
            if v is not None and str(v).strip().isdigit():
                return int(str(v).strip())
        return None

    def fetch(self, company: Dict, updated_since: Any = None) -> list[dict]:
        slug = str(company.get("ats_slug") or "").strip()
        if not slug:
            logger.warning("ats_slug is missing for traffit company")
            return []

        url = self._published_url(slug)
        all_rows: list[dict] = []
        page = 1

        while True:
            request_headers = {
                "X-Request-Page-Size": str(self.PAGE_SIZE),
                "X-Request-Current-Page": str(page),
                "Connection": "close",
            }
            resp = self.session.get(url, headers=request_headers)
            resp.raise_for_status()
            data = self._parse_json(resp, slug, context=f"page {page}")
            if not isinstance(data, list):
                raise ValueError(f"Traffit API did not return a list for {slug} (page {page})")

            for row in data:
                if isinstance(row, dict):
                    row["_ats_slug"] = slug
                    row["_incremental_at"] = row.get("valid_start")

            all_rows.extend(row for row in data if isinstance(row, dict))

            total_pages = self._header_int(resp.headers, "X-Result-Total-Pages", "x-result-total-pages")
            if total_pages is not None:
                if page >= total_pages or not data:
                    break
            elif not data or len(data) < self.PAGE_SIZE:
                break
            page += 1

        return self._filter_incremental_jobs(all_rows, updated_since, ["_incremental_at"])

    @staticmethod
    def _values_by_field_id(advert: dict) -> dict[str, str]:
        out: dict[str, str] = {}
        for entry in (advert or {}).get("values") or []:
            if not isinstance(entry, dict):
                continue
            fid = entry.get("field_id")
            if fid:
                out[str(fid)] = str(entry.get("value") or "")
        return out

    @staticmethod
    def _location_from_json_blob(raw: str | None) -> str:
        if not raw or not isinstance(raw, str):
            return ""
        text = raw.strip()
        if not text.startswith("{"):
            return ""
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return ""
        if not isinstance(obj, dict):
            return ""
        parts = [obj.get("locality"), obj.get("region1"), obj.get("country")]
        return ", ".join(str(p).strip() for p in parts if p and str(p).strip())

    def normalize(self, raw_job: Dict) -> Dict | None:
        slug = raw_job.get("_ats_slug")
        if not slug:
            logger.warning(
                "Traffit normalize missing _ats_slug",
                extra={"raw_job_id": raw_job.get("id")},
            )
            return None

        raw_id = raw_job.get("id")
        if raw_id is None:
            return None
        job_id = str(raw_id)

        advert_raw = raw_job.get("advert")
        advert: dict[str, Any] = advert_raw if isinstance(advert_raw, dict) else {}
        title = (advert.get("name") or "").strip()
        if not title:
            return None

        values_map = self._values_by_field_id(advert)
        options_raw = raw_job.get("options")
        options: dict[str, Any] = options_raw if isinstance(options_raw, dict) else {}

        desc_payload = {
            "description": values_map.get("description"),
            "requirements": values_map.get("requirements"),
            "responsibilities": values_map.get("responsibilities"),
            "what_we_offer": values_map.get("what_we_offer"),
        }
        description = self.build_description(
            desc_payload,
            [
                ("description", None),
                ("requirements", "Requirements"),
                ("responsibilities", "Responsibilities"),
                ("what_we_offer", "What we offer"),
            ],
        )

        loc_from_options = self._location_from_json_blob(options.get("job_location"))
        if not loc_from_options:
            loc_from_options = self._location_from_json_blob(values_map.get("geolocation"))
        location = loc_from_options

        remote_raw = options.get("remote")
        explicit_remote = str(remote_raw) == "1" or remote_raw is True

        extra_text = " ".join(v for v in values_map.values() if isinstance(v, str))
        is_remote = self.detect_remote(
            title,
            location,
            explicit_flag=explicit_remote,
            extra_text=extra_text,
        )

        scope_input = location if location else ("Remote" if explicit_remote else "")
        normalized_remote_scope = self.normalize_remote_scope(scope_input)

        source_url = sanitize_url(raw_job.get("url") or "") or ""
        if not source_url:
            return None

        department = options.get("branches")
        department_str = str(department).strip() if department else None

        company_name = str(slug).replace("-", " ").replace("_", " ").strip().title()

        return {
            "job_id": f"traffit:{slug}:{job_id}",
            "source": f"traffit:{slug}",
            "source_job_id": job_id,
            "title": title,
            "company_name": company_name,
            "description": description.strip(),
            "remote_scope": normalized_remote_scope,
            "remote_source_flag": is_remote,
            "source_url": source_url,
            "status": "new",
            "department": department_str,
        }

    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        if not str(slug or "").strip():
            return {}

        jobs = list(self.fetch(company={"ats_slug": slug}))
        if not jobs:
            return {}

        # API order is not guaranteed; use the latest valid_start for discovery freshness checks.
        starts = [str(j["valid_start"]) for j in jobs if isinstance(j, dict) and j.get("valid_start")]
        recent_at = max(starts) if starts else None

        return {
            "jobs_total": len(jobs),
            "remote_hits": sum(1 for j in jobs if isinstance(j, dict) and self._probe_job_remote(j)),
            "recent_job_at": recent_at,
        }

    def _probe_job_remote(self, raw_job: dict) -> bool:
        advert_raw = raw_job.get("advert")
        advert: dict[str, Any] = advert_raw if isinstance(advert_raw, dict) else {}
        title = (advert.get("name") or "").strip()
        values_map = self._values_by_field_id(advert)
        options_raw = raw_job.get("options")
        options: dict[str, Any] = options_raw if isinstance(options_raw, dict) else {}
        loc_from_options = self._location_from_json_blob(options.get("job_location"))
        if not loc_from_options:
            loc_from_options = self._location_from_json_blob(values_map.get("geolocation"))
        location = loc_from_options
        remote_raw = options.get("remote")
        explicit_remote = str(remote_raw) == "1" or remote_raw is True
        extra_text = " ".join(v for v in values_map.values() if isinstance(v, str))
        return self.detect_remote(
            title,
            location,
            explicit_flag=explicit_remote,
            extra_text=extra_text,
            is_probe=True,
        )


register(TraffitAdapter.source_name, TraffitAdapter)
