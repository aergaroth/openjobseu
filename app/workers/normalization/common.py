from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}


def sanitize_url(raw_url: Any) -> Optional[str]:
    if not isinstance(raw_url, str):
        return None

    value = raw_url.strip()
    if not value:
        return None

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value

    filtered_query = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_QUERY_PARAMS:
            continue
        filtered_query.append((key, val))

    clean_query = urlencode(filtered_query, doseq=True)
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, clean_query, "")
    )


def sanitize_location(raw_location: Any) -> Optional[str]:
    if not isinstance(raw_location, str):
        return None

    cleaned = " ".join(raw_location.split())
    return cleaned or None


def normalize_source_datetime(raw_value: Any) -> Optional[str]:
    if raw_value in (None, ""):
        return None

    dt: datetime | None = None

    if isinstance(raw_value, datetime):
        dt = raw_value
    elif isinstance(raw_value, struct_time):
        dt = datetime(*raw_value[:6], tzinfo=timezone.utc)
    elif isinstance(raw_value, (tuple, list)) and len(raw_value) >= 6:
        dt = datetime(*raw_value[:6], tzinfo=timezone.utc)
    elif isinstance(raw_value, (int, float)):
        dt = datetime.fromtimestamp(raw_value, tz=timezone.utc)
    elif isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return None

        dt = _parse_datetime_string(value)
        if dt is None:
            return None

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat()


def _parse_datetime_string(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
