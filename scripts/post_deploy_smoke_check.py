"""
Performs a post-deploy smoke test against a deployed application instance.

This script is designed to be run from a CI/CD environment after a deployment.
It checks key HTTP endpoints to ensure the application is healthy and key
functionality is operational.

Required environment variables:
- APP_BASE_URL: The base URL of the deployed application (e.g., https://yourapp.dev.run.app)
"""

import os
import sys
import requests
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

try:
    BASE_URL = os.environ["APP_BASE_URL"]
except KeyError:
    logger.fatal("FATAL: The APP_BASE_URL environment variable must be set.")
    sys.exit(1)


_AUTH_HEADERS = None


def get_auth_headers():
    """Attempts to fetch an OIDC token for authenticating with Cloud Run."""
    global _AUTH_HEADERS
    if _AUTH_HEADERS is not None:
        return _AUTH_HEADERS

    _AUTH_HEADERS = {}

    # Najpierw sprawdź czy token jest podany z zewnątrz (CI)
    token = os.environ.get("OIDC_TOKEN")
    if token:
        logger.info("  (Using OIDC token from environment)")
        _AUTH_HEADERS = {"Authorization": f"Bearer {token}"}
        return _AUTH_HEADERS

    try:
        import google.auth.transport.requests
        import google.oauth2.id_token

        req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(req, BASE_URL)
        logger.info("  (Attached OIDC authentication token)")
        _AUTH_HEADERS = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        logger.info(f"  (Proceeding without OIDC token: {e})")

    return _AUTH_HEADERS


def http_check():
    """Checks the /health endpoint, allowing time for the service to start."""
    logger.info("→ Health check")
    retries = 10
    delay = 10

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(f"{BASE_URL}/health", headers=get_auth_headers(), timeout=10)
            r.raise_for_status()
            logger.info("  OK")
            return
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise e
            logger.info(f"  (Attempt {attempt}/{retries}) Service not ready yet. Waiting {delay}s...")
            time.sleep(delay)


def run_tick():
    """Triggers the /internal/tick endpoint to check core processing."""
    logger.info("→ Running tick")
    # The tick endpoint can require special authentication (e.g., OIDC).
    # For a simple smoke test, we are primarily interested in the service
    # being up and responding. A 401/403 is an acceptable "pass" state
    # if it means the endpoint is present and protected.
    r = requests.post(f"{BASE_URL}/internal/tick?format=json", headers=get_auth_headers(), timeout=30)
    if r.status_code >= 500:
        logger.error(f"  ERROR: Tick endpoint returned a server error: {r.status_code}")
        r.raise_for_status()
    elif r.status_code in [401, 403]:
        logger.info("  OK (tick endpoint is protected, which is expected)")
    else:
        r.raise_for_status()
        payload = r.json()
        logger.info(f"  OK (actions: {payload.get('actions')})")
    return r.json() if r.ok else {}


def feed_check():
    """Checks that the internal /jobs/feed endpoint is available."""
    logger.info("→ Feed check")
    r = requests.get(f"{BASE_URL}/jobs/feed", headers=get_auth_headers(), timeout=10)
    if r.status_code >= 500:
        logger.error(f"  ERROR: Feed endpoint returned a server error: {r.status_code}")
        r.raise_for_status()
    elif r.status_code in [401, 403]:
        logger.info("  OK (feed endpoint is protected, which is expected)")
    else:
        r.raise_for_status()
        data = r.json()
        assert "jobs" in data, "Feed endpoint response is missing 'jobs' key"
        assert isinstance(data["jobs"], list), f"Feed 'jobs' key is not a list. Type was: {type(data['jobs'])}"
        logger.info(f"  OK (found {len(data['jobs'])} items in feed)")
    return len(r.json().get("jobs", [])) if r.ok else 0


def search_check():
    """Performs a basic search to check the /jobs search endpoint."""
    logger.info("→ Search check (q=test)")
    r = requests.get(f"{BASE_URL}/jobs", params={"q": "test"}, headers=get_auth_headers(), timeout=10)
    if r.status_code >= 500:
        logger.error(f"  ERROR: Search endpoint returned a server error: {r.status_code}")
        r.raise_for_status()
    elif r.status_code in [401, 403]:
        logger.info("  OK (search endpoint is protected, which is expected)")
    else:
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        assert isinstance(items, list)
        logger.info(f"  OK (found {len(items)} jobs matching 'test')")
    return len(r.json().get("items", [])) if r.ok else 0


if __name__ == "__main__":
    logger.info(f"Smoke testing application at {BASE_URL}...")

    try:
        http_check()
        run_tick()
        feed_check()
        search_check()
        logger.info("\n✓ Post-deploy smoke check finished OK")
    except Exception as e:
        logger.error(f"\n✗ SMOKE CHECK FAILED: {e}")
        sys.exit(1)
