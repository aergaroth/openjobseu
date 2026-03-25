from enum import Enum


class RemoteClass(str, Enum):
    REMOTE_ONLY = "remote_only"
    REMOTE_REGION_LOCKED = "remote_region_locked"
    REMOTE_OPTIONAL = "remote_optional"
    NON_REMOTE = "non_remote"
    UNKNOWN = "unknown"


class GeoClass(str, Enum):
    EU_MEMBER_STATE = "eu_member_state"
    EU_EXPLICIT = "eu_explicit"
    EU_REGION = "eu_region"
    UK = "uk"
    NON_EU = "non_eu"
    UNKNOWN = "unknown"
