from datetime import datetime, timezone
from app.adapters.ats.utils import (
    sanitize_url,
    sanitize_location,
    normalize_source_datetime,
    to_utc_datetime,
)


def test_sanitize_url():
    assert sanitize_url(None) is None
    assert sanitize_url(123) is None
    assert sanitize_url("  ") is None
    assert sanitize_url("not a url") == "not a url"

    # Usunięcie query params śledzących (np. utm_*, fbclid) i zachowanie istotnych
    assert sanitize_url("https://example.com/job?utm_source=foo&gclid=bar&valid=1") == "https://example.com/job?valid=1"
    assert sanitize_url("http://example.com/test?fbclid=123") == "http://example.com/test"


def test_sanitize_location():
    assert sanitize_location(None) is None
    assert sanitize_location(123) is None
    assert sanitize_location("   Berlin   Germany  ") == "Berlin Germany"
    assert sanitize_location("   ") is None


def test_normalize_source_datetime():
    assert normalize_source_datetime(None) is None
    assert normalize_source_datetime("") is None

    import time

    st = time.gmtime(1600000000)
    assert normalize_source_datetime(st) == datetime.fromtimestamp(1600000000, tz=timezone.utc).isoformat()

    # Mechanizm odróżniania milisekund od sekund
    assert normalize_source_datetime(1600000000) == datetime.fromtimestamp(1600000000, tz=timezone.utc).isoformat()
    assert normalize_source_datetime(1600000000000) == datetime.fromtimestamp(1600000000, tz=timezone.utc).isoformat()

    assert normalize_source_datetime("   ") is None
    assert normalize_source_datetime("invalid-date") is None
    assert "2023-01-01" in normalize_source_datetime("Sun, 01 Jan 2023 12:00:00 GMT")


def test_to_utc_datetime():
    assert to_utc_datetime(None) is None
    dt = to_utc_datetime("2023-01-01T12:00:00Z")
    assert dt.year == 2023
    assert dt.tzinfo == timezone.utc
