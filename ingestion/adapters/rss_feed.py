import feedparser
from datetime import datetime, timezone

class RssFeedAdapter:
    source = "rss_feed"

    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    def fetch(self) -> list[dict]:
        feed = feedparser.parse(self.feed_url)
        return feed.entries

    def normalize(self, entry: dict) -> dict:
        return {
            "job_id": f"{self.source}:{entry.get('id', entry.get('link'))}",
            "source": self.source,
            "source_job_id": entry.get('id', entry.get('link')),
            "source_url": entry.get('link'),
            "title": entry.get('title'),
            "company_name": entry.get('author', 'unknown'),
            "description": entry.get('summary', ''),
            "remote": True,
            "remote_scope": "EU-wide",
            "status": "active",
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
        }
