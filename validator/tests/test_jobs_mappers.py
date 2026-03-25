from app.domain.jobs.enums import GeoClass, RemoteClass
from app.domain.jobs.mappers import normalize_geo_class, normalize_remote_class


def test_normalize_remote_class():
    # Edge cases: None and empty string
    assert normalize_remote_class(None) == RemoteClass.UNKNOWN
    assert normalize_remote_class("   ") == RemoteClass.UNKNOWN

    # Legacy mappings
    assert normalize_remote_class("hybrid") == RemoteClass.NON_REMOTE
    assert normalize_remote_class("remote_but_geo_restricted") == RemoteClass.REMOTE_REGION_LOCKED

    # Valid Enum casting
    assert normalize_remote_class("remote_only") == RemoteClass.REMOTE_ONLY

    # Invalid string (ValueError fallback)
    assert normalize_remote_class("invalid_string_xyz") == RemoteClass.UNKNOWN


def test_normalize_geo_class():
    # Edge cases: None and empty string
    assert normalize_geo_class(None) == GeoClass.UNKNOWN
    assert normalize_geo_class("") == GeoClass.UNKNOWN

    # Legacy mappings
    assert normalize_geo_class("eog") == GeoClass.EU_REGION
    assert normalize_geo_class("worldwide") == GeoClass.UNKNOWN

    # Valid Enum casting
    assert normalize_geo_class("eu_member_state") == GeoClass.EU_MEMBER_STATE

    # Invalid string (ValueError fallback)
    assert normalize_geo_class("invalid_string_xyz") == GeoClass.UNKNOWN
