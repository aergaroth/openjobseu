from .enums import GeoClass, RemoteClass


LEGACY_REMOTE_CLASS_MAP: dict[str, RemoteClass] = {
    "remote_but_geo_restricted": RemoteClass.REMOTE_REGION_LOCKED,
    "hybrid": RemoteClass.NON_REMOTE,
    "office_first": RemoteClass.NON_REMOTE,
}


LEGACY_GEO_CLASS_MAP: dict[str, GeoClass] = {
    "eu_member_state": GeoClass.EU_MEMBER_STATE,
    "eu_explicit": GeoClass.EU_EXPLICIT,
    "eu_region": GeoClass.EU_REGION,
    "eog": GeoClass.EU_REGION,
    "uk": GeoClass.UK,
    "worldwide": GeoClass.UNKNOWN,
    "global": GeoClass.UNKNOWN,
    "eu_friendly": GeoClass.UNKNOWN,
    "non_eu": GeoClass.NON_EU,
    "non_eu_restricted": GeoClass.NON_EU,
    "unknown": GeoClass.UNKNOWN,
}


EU_ELIGIBLE_GEO_CLASSES: frozenset[GeoClass] = frozenset(
    {
        GeoClass.EU_MEMBER_STATE,
        GeoClass.EU_EXPLICIT,
        GeoClass.EU_REGION,
        GeoClass.UK,
    }
)

