import os
import logging
from fastapi import Request, HTTPException, status
from google.oauth2 import id_token
from google.auth.transport import requests


logger = logging.getLogger(__name__)


def require_internal_access(request: Request):
    """
    Protect internal endpoints.

    Allowed:
    - localhost (development)
    - TestClient (for unit/integration tests)
    - requests presenting the correct internal secret
    """

    client_host = request.client.host if request.client else None

    # Allow local development and test runs
    if client_host in ("127.0.0.1", "localhost", "testclient"):
        return

    # 1. Fallback: Validate using a shared secret (local dev or backward compat)
    expected_secret = os.getenv("INTERNAL_SECRET")
    provided_secret = request.headers.get("X-Internal-Secret")

    if expected_secret and provided_secret == expected_secret:
        return

    # 2. GCP OIDC Token Validation (Cloud Scheduler or Administrator's gcloud token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            # Verify token signature and expiration without requiring a specific audience
            id_info = id_token.verify_oauth2_token(token, requests.Request(), audience=None)
            
            # Check if token belongs to an authorized service account or admin email
            email = id_info.get("email")
            allowed_emails = [
                os.getenv("ALLOWED_AUTH_EMAIL"),
                os.getenv("SCHEDULER_SA_EMAIL")
            ]
            
            if email and email in allowed_emails:
                return
            logger.warning("OIDC token contains unauthorized email: %s", email)
        except Exception as e:
            logger.warning("OIDC token verification failed: %s", str(e))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required for internal endpoints",
    )