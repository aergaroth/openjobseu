from .constants import LEGACY_GEO_CLASS_MAP, LEGACY_REMOTE_CLASS_MAP
from .enums import GeoClass, RemoteClass


def normalize_remote_class(value: str | None) -> RemoteClass:
    if not value:
        return RemoteClass.UNKNOWN

    value = value.strip().lower()

    if value in LEGACY_REMOTE_CLASS_MAP:
        return LEGACY_REMOTE_CLASS_MAP[value]

    try:
        return RemoteClass(value)
    except ValueError:
        return RemoteClass.UNKNOWN


def normalize_geo_class(value: str | None) -> GeoClass:
    if not value:
        return GeoClass.UNKNOWN

    value = value.strip().lower()

    if value in LEGACY_GEO_CLASS_MAP:
        return LEGACY_GEO_CLASS_MAP[value]

    try:
        return GeoClass(value)
    except ValueError:
        return GeoClass.UNKNOWN
