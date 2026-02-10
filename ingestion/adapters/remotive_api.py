import requests

class RemotiveApiAdapter:
    source = "remotive"

    API_URL = "https://remotive.com/api/remote-jobs"

    def fetch(self) -> list[dict]:
        resp = requests.get(self.API_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("jobs", [])
