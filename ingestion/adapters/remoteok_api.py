import requests
from typing import List, Dict


class RemoteOkApiAdapter:
    """
    Fetch-only adapter for RemoteOK public API.

    Source:
    https://remoteok.com/api

    Notes:
    - First element is metadata (legal notice)
    - Remaining elements are job offers
    - No logging here by design
    """

    source = "remoteok"
    API_URL = "https://remoteok.com/api"

    def fetch(self) -> List[Dict]:
        resp = requests.get(
            self.API_URL,
            headers={
                "User-Agent": "OpenJobsEU/1.0 (https://openjobseu.org)",
                "Accept": "application/json",
            },
            timeout=15,
        )

        resp.raise_for_status()

        data = resp.json()

        if not isinstance(data, list):
            raise ValueError("RemoteOK API did not return a list")

        if not data:
            return []

        # First element is metadata, skip it
        return data[1:]
