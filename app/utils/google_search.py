import os
import requests
import logging

logger = logging.getLogger(__name__)


def google_custom_search(query: str, num_results: int = 10, start: int = 1) -> list[str]:
    """
    Performs a Google Custom Search and returns a list of URLs.

    Args:
        query (str): The search query.
        num_results (int): The number of results to retrieve (max 10 per request).
        start (int): The index of the first result to return.

    Returns:
        list[str]: A list of result URLs.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx_id = os.environ.get("GOOGLE_CSE_ID")

    if not api_key:
        logger.warning("GOOGLE_API_KEY environment variable not set. Skipping Google search.")
        return []
    if not cx_id:
        logger.warning("GOOGLE_CSE_ID environment variable not set. Skipping Google search.")
        return []

    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx_id,
        "q": query,
        "num": num_results,
        "start": start,
    }

    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        search_results = response.json()

        if "items" in search_results:
            return [item.get("link", "") for item in search_results["items"]]
        else:
            return []

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during Google Custom Search API request: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Google search: {e}")
        return []
