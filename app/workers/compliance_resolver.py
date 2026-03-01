from typing import Dict


def _normalize_remote_class(remote_class: str | None) -> str:
    value = str(remote_class or "").strip().lower()

    if value in {
        "remote_only",
        "remote_region_locked",
        "remote_optional",
        "unknown",
        "non_remote",
    }:
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

    # 2) Fully remote
    if remote == "remote_only" and geo in {
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
    }:
        return 100, "approved"

    # 3) Region-locked remote (EU)
    if remote == "remote_region_locked" and geo in {
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
    }:
        return 90, "approved"

    # 4) Optional remote (benefit)
    if remote == "remote_optional" and geo in {
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
    }:
        return 60, "review"

    # 5) Unknown remote but EU geo
    if remote == "unknown" and geo in {
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
    }:
        return 55, "review"

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
