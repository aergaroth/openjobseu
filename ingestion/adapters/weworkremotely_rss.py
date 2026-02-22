import feedparser


class WeWorkRemotelyRssAdapter:
    source = "weworkremotely"

    FEED_URLS = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-product-jobs.rss",
    ]

    def fetch(self) -> list[dict]:
        """
        Fetch jobs from multiple WeWorkRemotely RSS feeds
        and deduplicate by link.
        """

        all_entries: list[dict] = []
        seen_links: set[str] = set()

        for url in self.FEED_URLS:
            feed = feedparser.parse(url)
            entries = feed.entries or []

            for entry in entries:
                link = entry.get("link")
                if not link:
                    continue

                if link in seen_links:
                    continue

                seen_links.add(link)
                all_entries.append(entry)

        return all_entries
