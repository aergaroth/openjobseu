import uuid
from datetime import datetime, timezone
from typing import Dict


def normalize_example_source_job(raw: Dict) -> Dict:
    """
    Normalize a local example-source payload into the canonical model.
    Development-only helper, not used by production ingestion workers.
    """
    now = datetime.now(timezone.utc).isoformat()

    return {
        "job_id": str(uuid.uuid4()),
        "source": "example_source",
        "source_job_id": raw.get("id"),
        "source_url": raw.get("url"),
        "title": raw.get("title"),
        "company_name": raw.get("company", {}).get("name"),
        "description": raw.get("description"),
        "employment_type": raw.get("employment_type"),
        "seniority": "unspecified",
        "remote_source_flag": True,
        "remote_scope": raw.get("remote_scope"),
        "country_restrictions": None,
        "tech_tags": raw.get("technologies", []),
        "status": "active",
        "first_seen_at": now,
        "last_seen_at": now,
        "last_verified_at": None,
        "verification_failures": 0,
        "created_at": now,
        "updated_at": now,
    }
