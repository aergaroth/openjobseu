from fastapi import Request, HTTPException, status

INTERNAL_ACCESS_HEADER = "X-Serverless-Authorization"


def require_internal_access(request: Request):
    """
    Dependency to protect internal endpoints.

    Allows requests from:
    - localhost
    - Cloud Run / Scheduler (via X-Serverless-Authorization header)
    """

    client_host = request.client.host if request.client else None
    headers = request.headers

    is_localhost = client_host in ("127.0.0.1", "localhost")
    has_internal_header = bool(headers.get(INTERNAL_ACCESS_HEADER))

    if not (is_localhost or has_internal_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to internal endpoints is restricted.",
        )
    