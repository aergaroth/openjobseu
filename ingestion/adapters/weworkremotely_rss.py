import feedparser
from datetime import datetime, timezone

class WeWorkRemotelyRssAdapter:
    source = "weworkremotely"

    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    def fetch(self) -> list[dict]:
        feed = feedparser.parse(self.feed_url)
        return feed.entries

    def normalize(self, entry: dict) -> dict:
        raw_title = entry.get("title", "").strip()

        company = entry.get("author") or "unknown"
        title = raw_title

        # Safe heuristic: extract company from "Company: Job Title"
        if company == "unknown" and ":" in raw_title:
            possible_company, possible_title = raw_title.split(":", 1)

            # very defensive checks
            if 2 <= len(possible_company) <= 80:
                company = possible_company.strip()
                title = possible_title.strip()

        return {
            "job_id": f"{self.source}:{entry.get('id', entry.get('link'))}",
            "source": self.source,
            "source_job_id": entry.get('id', entry.get('link')),
            "source_url": entry.get('link'),
            "title": title,
            "company_name": company,
            "description": entry.get('summary', ''),
            "remote": True,
            "remote_scope": "EU-wide",
            "status": "new",
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
        }

