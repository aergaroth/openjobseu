import os
import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://google.serper.dev/search"
_TIMEOUT = 15


def serper_search(query: str, num_results: int = 10, page: int = 1) -> list[str]:
    """
    Searches via Serper.dev (Google SERP proxy) and returns a list of URLs.
    Uses SERPER_API_KEY env var. Returns [] if key is missing or on any error.
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return []

    payload = {"q": query, "num": num_results, "page": page}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        resp = requests.post(_BASE_URL, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return [item.get("link", "") for item in data.get("organic", []) if item.get("link")]
    except requests.exceptions.RequestException as e:
        logger.error(f"Serper search request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error during Serper search: {e}")
        return []
