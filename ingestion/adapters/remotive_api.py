import requests
from datetime import datetime, timezone

class RemotiveApiAdapter:
    source = "remotive"

    API_URL = "https://remotive.com/api/remote-jobs"

    def fetch(self) -> list[dict]:
        resp = requests.get(self.API_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("jobs", [])

    def normalize(self, job: dict) -> dict:
        """
        Map Remotive job JSON -> canonical job model.
        No heuristics, no enrichment, no guessing.
        """

        now = datetime.now(timezone.utc).isoformat()

        return {
            "job_id": f"{self.source}:{job['id']}",
            "source": self.source,
            "source_job_id": str(job["id"]),
            "source_url": job["url"],

            "title": job["title"],
            "company_name": job["company_name"],
            "description": job.get("description", ""),

            # Remotive is remote-only by definition
            "remote": True,

            # RAW value – normalization comes later
            # Examples: "Worldwide", "Europe", "USA only", "Germany"
            "remote_scope": job.get("candidate_required_location", "unknown"),

            "status": "new",

            # lifecycle fields (aligned with rss adapter)
            "first_seen_at": now,
        }
