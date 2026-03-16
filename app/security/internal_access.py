import os
from fastapi import Request, HTTPException, status


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

    # Validate using a shared secret injected by infrastructure
    expected_secret = os.getenv("INTERNAL_SECRET")
    provided_secret = request.headers.get("X-Internal-Secret")

    if expected_secret and provided_secret == expected_secret:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required for internal endpoints",
    )