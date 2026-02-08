from datetime import datetime, timezone
from typing import Optional, Dict


def normalize_remotive_job(raw: Dict) -> Optional[Dict]:
    """
    Normalize a single Remotive job into the OpenJobsEU canonical model.

    Policy:
    - Accept only EU-wide or Worldwide jobs
    - Skip US-only / non-EU locations
    """

    # Required fields
    job_id = raw.get("id")
    title = raw.get("title")
    company = raw.get("company_name")
    description = raw.get("description")
    url = raw.get("url")
    location = raw.get("candidate_required_location")

    if not all([job_id, title, company, description, url, location]):
        return None

    location_lower = location.lower()

    # OpenJobsEU policy: EU-wide or worldwide only
    if "europe" not in location_lower and "worldwide" not in location_lower:
        return None

    now = datetime.now(timezone.utc).isoformat()

    return {
        "job_id": f"remotive:{job_id}",
        "source": "remotive",
        "source_job_id": str(job_id),
        "source_url": url,
        "title": title.strip(),
        "company_name": company.strip(),
        "description": description.strip(),
        "remote": True,
        "remote_scope": location,
        "status": "new",
        "first_seen_at": now,
        "last_seen_at": now,
    }
