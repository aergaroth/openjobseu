import hashlib
import logging
from datetime import date

from fastapi import HTTPException, Request, status

from storage.repositories.api_keys_repository import get_key_by_hash, increment_and_check_quota

logger = logging.getLogger(__name__)

_KEY_PREFIX = "ojeu_"
_KEY_LENGTH = 37  # "ojeu_" (5) + token_urlsafe(24) (32 chars)


def require_api_key(request: Request) -> dict:
    """FastAPI dependency that validates a paid API key.

    Reads the Authorization: Bearer <key> header, validates the key against
    the database, and enforces the daily request quota.

    Returns:
        Dict with key metadata (key_id, tier, quota_per_day, etc.).

    Raises:
        HTTPException 401: Missing, malformed, invalid, or revoked key.
        HTTPException 429: Daily quota exceeded.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer ojeu_<key>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = auth_header.removeprefix("Bearer ").strip()

    if not raw_key.startswith(_KEY_PREFIX) or len(raw_key) != _KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key = get_key_by_hash(key_hash)

    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not key["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    today = date.today()
    new_count, quota = increment_and_check_quota(key["key_id"], today)

    if quota != -1 and new_count > quota:
        logger.warning(
            "api_key_quota_exceeded",
            extra={"key_id": key["key_id"], "tier": key["tier"], "count": new_count, "quota": quota},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota exceeded. Tier '{key['tier']}' allows {quota} requests/day.",
            headers={"Retry-After": "86400"},
        )

    return key
