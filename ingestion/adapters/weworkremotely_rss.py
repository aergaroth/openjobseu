import feedparser

class WeWorkRemotelyRssAdapter:
    source = "weworkremotely"

    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    def fetch(self) -> list[dict]:
        feed = feedparser.parse(self.feed_url)
        return feed.entries
