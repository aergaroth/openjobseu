from typing import Dict, List

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
        "remote_only",
        "remote_but_geo_restricted",
        "non_remote",
        "unknown",
        # Backward-compatibility alias still present in some historical rows.
        "remote_region_locked",
    ],
    "geo_class": [
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
        "non_eu",
        "unknown",
    ],
    "compliance_status": [
        "approved",
        "review",
        "rejected",
    ],
}


def get_audit_filter_registry() -> Dict[str, List[str]]:
    return {key: list(values) for key, values in AUDIT_FILTER_REGISTRY.items()}
