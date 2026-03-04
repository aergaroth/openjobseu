from typing import Dict, List

from app.domain.classification.enums import ComplianceStatus, GeoClass, RemoteClass

# Canonical filter values used by the internal audit panel.
AUDIT_FILTER_REGISTRY: Dict[str, List[str]] = {
    "status": [
        "new",
        "active",
        "stale",
        "expired",
        "unreachable",
    ],
    "remote_class": [
        RemoteClass.REMOTE_ONLY.value,
        RemoteClass.REMOTE_REGION_LOCKED.value,
        RemoteClass.NON_REMOTE.value,
        RemoteClass.REMOTE_OPTIONAL.value,
        RemoteClass.UNKNOWN.value,
        # Backward-compatibility alias still present in some historical rows.
        "remote_but_geo_restricted",
    ],
    "geo_class": [
        GeoClass.EU_MEMBER_STATE.value,
        GeoClass.EU_EXPLICIT.value,
        GeoClass.EU_REGION.value,
        GeoClass.UK.value,
        GeoClass.NON_EU.value,
        GeoClass.UNKNOWN.value,
    ],
    "compliance_status": [
        ComplianceStatus.APPROVED.value,
        ComplianceStatus.REVIEW.value,
        ComplianceStatus.REJECTED.value,
    ],
}


def get_audit_filter_registry() -> Dict[str, List[str]]:
    return {key: list(values) for key, values in AUDIT_FILTER_REGISTRY.items()}
