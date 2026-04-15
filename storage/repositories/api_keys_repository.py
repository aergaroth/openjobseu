import hashlib
import secrets
import uuid
from datetime import date

from sqlalchemy import text

from storage.db_engine import get_engine

TIER_QUOTAS: dict[str, int] = {
    "free": 500,
    "pro": 10_000,
    "enterprise": -1,
}

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def create_api_key(label: str, tier: str) -> dict:
    """Generate and persist a new API key.

    Args:
        label: Human-readable name (e.g. "Acme Corp - prod").
        tier: One of "free", "pro", "enterprise".

    Returns:
        Dict with key_id, raw_key (only shown once), label, tier, quota_per_day.
    """
    raw_key = "ojeu_" + secrets.token_urlsafe(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = str(uuid.uuid4())
    quota = TIER_QUOTAS[tier]
    today = date.today()

    with _get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO api_keys (key_id, key_hash, label, tier, quota_per_day, quota_reset_date)
                VALUES (:key_id, :key_hash, :label, :tier, :quota_per_day, :today)
            """),
            {
                "key_id": key_id,
                "key_hash": key_hash,
                "label": label,
                "tier": tier,
                "quota_per_day": quota,
                "today": today,
            },
        )

    return {
        "key_id": key_id,
        "raw_key": raw_key,
        "label": label,
        "tier": tier,
        "quota_per_day": quota,
    }


def get_key_by_hash(key_hash: str) -> dict | None:
    """Look up an API key by its SHA-256 hash.

    Args:
        key_hash: Hex-encoded SHA-256 digest of the raw key.

    Returns:
        Key metadata dict, or None if not found.
    """
    with _get_engine().connect() as conn:
        row = (
            conn.execute(
                text("""
                    SELECT key_id, label, tier, quota_per_day, requests_today,
                           quota_reset_date, is_active, last_used_at
                    FROM api_keys
                    WHERE key_hash = :key_hash
                """),
                {"key_hash": key_hash},
            )
            .mappings()
            .first()
        )
    return dict(row) if row else None


def increment_and_check_quota(key_id: str, today: date) -> tuple[int, int]:
    """Atomically increment the request counter and return (new_count, quota_per_day).

    Resets the daily counter when quota_reset_date is stale.
    Uses a single UPDATE … RETURNING to avoid TOCTOU race conditions
    under concurrent Cloud Run instances.

    Args:
        key_id: The key's UUID.
        today: Current UTC date used for quota window comparison.

    Returns:
        Tuple of (new requests_today value, quota_per_day).
    """
    with _get_engine().begin() as conn:
        row = (
            conn.execute(
                text("""
                    UPDATE api_keys
                    SET
                        requests_today = CASE
                            WHEN quota_reset_date IS NULL OR quota_reset_date < :today THEN 1
                            ELSE requests_today + 1
                        END,
                        quota_reset_date = :today,
                        last_used_at = NOW()
                    WHERE key_id = :key_id
                    RETURNING requests_today, quota_per_day
                """),
                {"key_id": key_id, "today": today},
            )
            .mappings()
            .one()
        )
    return int(row["requests_today"]), int(row["quota_per_day"])


def list_api_keys() -> list[dict]:
    """Return all API keys ordered by creation date, without key_hash."""
    with _get_engine().connect() as conn:
        rows = (
            conn.execute(
                text("""
                    SELECT key_id, label, tier, quota_per_day, requests_today,
                           quota_reset_date, is_active, created_at, last_used_at
                    FROM api_keys
                    ORDER BY created_at DESC
                """)
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def revoke_api_key(key_id: str) -> None:
    """Deactivate an API key by setting is_active = false.

    Args:
        key_id: The key's UUID.
    """
    with _get_engine().begin() as conn:
        conn.execute(
            text("UPDATE api_keys SET is_active = false WHERE key_id = :key_id"),
            {"key_id": key_id},
        )
