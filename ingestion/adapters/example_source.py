# Adapter responsibility:
# - fetch raw job data
# - normalize to canonical model
# - MUST NOT set job lifecycle status or perform availability checks


import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ExampleSourceAdapter:
    SOURCE_ID = "example_source"

    def __init__(self):
        self.source_file = Path("ingestion/sources/example_jobs.json")

    def fetch(self) -> list[dict]:
        with self.source_file.open() as f:
            payload = json.load(f)
        return payload.get("jobs", [])

    def normalize(self, raw_job: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()

        return {
            "job_id": str(uuid.uuid4()),
            "source": self.SOURCE_ID,
            "source_job_id": raw_job.get("id"),
            "source_url": raw_job.get("url"),
            "title": raw_job.get("title"),
            "company_name": raw_job.get("company", {}).get("name"),
            "description": raw_job.get("description"),
            "employment_type": raw_job.get("employment_type"),
            "seniority": "unspecified",
            "remote": True,
            "remote_scope": raw_job.get("remote_scope"),
            "country_restrictions": None,
            "tech_tags": raw_job.get("technologies", []),
            "status": "active",
            "first_seen_at": now,
            "last_seen_at": now,
            "last_verified_at": None,
            "verification_failures": 0,
            "created_at": now,
            "updated_at": now,
        }

    def run(self) -> list[dict]:
        raw_jobs = self.fetch()
        return [self.normalize(job) for job in raw_jobs]
