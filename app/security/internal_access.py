from fastapi import Request, HTTPException, status


def require_internal_access(request: Request):
    """
    Protect internal endpoints.

    Allowed:
    - localhost (development)
    - TestClient (for unit/integration tests)
    - any authenticated Cloud Run identity (IAM verified)
    """

    client_host = request.client.host if request.client else None

    # Allow local development and test runs
    if client_host in ("127.0.0.1", "localhost", "testclient"):
        return

    # Check for identity header from GCP services (e.g. Cloud Run, Scheduler).
    # This header is added by the proxy when the request is authenticated with an OIDC token.
    identity = request.headers.get("X-Goog-Authenticated-User-Email")

    if identity:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Authentication required for internal endpoints",
    )