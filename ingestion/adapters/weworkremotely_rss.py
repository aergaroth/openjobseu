import feedparser

class WeWorkRemotelyRssAdapter:
    source = "weworkremotely"
    FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def fetch(self) -> list[dict]:
        feed = feedparser.parse(self.FEED_URL)
        return feed.entries
