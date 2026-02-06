import logging
import requests
from typing import List, Dict

logger = logging.getLogger("openjobseu.ingestion.remoteok")


class RemoteOKApiAdapter:
    """
    Fetch-only adapter for RemoteOK public API.

    Source:
    https://remoteok.com/api

    Notes:
    - First element is metadata (legal notice)
    - Remaining elements are job offers
    - No normalization or persistence here (by design)
    """

    source = "remoteok"
    API_URL = "https://remoteok.com/api"

    def fetch(self) -> List[Dict]:
        logger.info("remoteok fetch started")

        resp = requests.get(
            self.API_URL,
            headers={
                # RemoteOK expects a browser-like UA
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
            logger.warning("remoteok returned empty list")
            return []

        # First element is metadata, skip it
        jobs = data[1:]

        logger.info(
            "remoteok fetch completed",
            extra={
                "total_raw": len(data),
                "jobs": len(jobs),
                "first_job_keys": list(jobs[0].keys()) if jobs else [],
            },
        )

        return jobs
