from typing import Dict


def _normalize_remote_class(remote_class: str | None) -> str:
    value = str(remote_class or "").strip().lower()
    if value in {
        "remote_only",
        "remote_but_geo_restricted",
        "remote_region_locked",
        "unknown",
        "non_remote",
    }:
        if value == "remote_region_locked":
            return "remote_but_geo_restricted"
        return value
    if value in {"office_first", "hybrid"}:
        return "non_remote"
    return "unknown"


def _normalize_geo_class(geo_class: str | None) -> str:
    value = str(geo_class or "").strip().lower()
    aliases = {
        "eu_member_state": "eu_member_state",
        "eu_region": "eu_region",
        "eu_explicit": "eu_explicit",
        "eog": "eu_region",
        "uk": "uk",
        "worldwide": "unknown",
        "global": "unknown",
        "eu_friendly": "unknown",
        "non_eu": "non_eu",
        "non_eu_restricted": "non_eu",
        "unknown": "unknown",
    }
    return aliases.get(value, "unknown")


def _resolve_score_and_status(remote_class: str | None, geo_class: str | None) -> tuple[int, str]:
    remote = _normalize_remote_class(remote_class)
    geo = _normalize_geo_class(geo_class)

    # 1) Hard reject
    if remote == "non_remote":
        return 0, "rejected"
    if geo == "non_eu":
        return 0, "rejected"

    # 2) remote_only
    if remote == "remote_only" and geo == "eu_member_state":
        return 100, "approved"
    if remote == "remote_only" and geo == "eu_explicit":
        return 90, "approved"
    if remote == "remote_only" and geo == "eu_region":
        return 90, "approved"
    if remote == "remote_only" and geo == "uk":
        return 85, "approved"

    # 3) remote_but_geo_restricted
    if remote == "remote_but_geo_restricted" and geo == "eu_member_state":
        return 70, "review"
    if remote == "remote_but_geo_restricted" and geo == "eu_explicit":
        return 65, "review"
    if remote == "remote_but_geo_restricted" and geo == "eu_region":
        return 65, "review"

    # 4) unknown remote
    if remote == "unknown" and geo == "eu_member_state":
        return 60, "review"
    if remote == "unknown" and geo == "eu_explicit":
        return 55, "review"
    if remote == "unknown" and geo == "eu_region":
        return 55, "review"
    if remote == "unknown" and geo == "uk":
        return 55, "review"

    # 5) everything else
    return 20, "rejected"


def calculate_compliance_score(remote_class: str | None, geo_class: str | None) -> int:
    score, _status = _resolve_score_and_status(remote_class, geo_class)
    return score


def resolve_compliance(remote_class: str | None, geo_class: str | None) -> Dict:
    """
    Returns:
        {
            "compliance_status": str,
            "compliance_score": int
        }
    """
    score, status = _resolve_score_and_status(remote_class, geo_class)
    return {
        "compliance_status": status,
        "compliance_score": score,
    }
