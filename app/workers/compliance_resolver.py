from typing import Dict


def _clamp_score(score: int) -> int:
    return max(0, min(score, 100))


def calculate_compliance_score(remote_class: str | None, geo_class: str | None) -> int:
    score = 0

    # Remote scoring
    if remote_class == "remote_only":
        score += 40
    elif remote_class == "unknown":
        score += 10
    elif remote_class == "remote_but_geo_restricted":
        score -= 20
    elif remote_class == "non_remote":
        score -= 100

    # Geo scoring
    if geo_class == "eu_explicit":
        score += 40
    elif geo_class == "eu_friendly":
        score += 25
    elif geo_class == "non_eu":
        score -= 100

    return _clamp_score(score)


def resolve_compliance(remote_class: str | None, geo_class: str | None) -> Dict:
    """
    Returns:
        {
            "compliance_status": str,
            "compliance_score": int
        }
    """

    # Hard rejects
    if remote_class == "non_remote":
        return {"compliance_status": "rejected", "compliance_score": 0}

    if geo_class == "non_eu":
        return {"compliance_status": "rejected", "compliance_score": 0}

    # Approved
    if (
        remote_class == "remote_only"
        and geo_class in ("eu_explicit", "eu_friendly")
    ):
        score = calculate_compliance_score(remote_class, geo_class)
        return {"compliance_status": "approved", "compliance_score": score}

    # Review (risk bucket)
    if (
        remote_class == "unknown"
        and geo_class in ("eu_explicit", "eu_friendly")
    ):
        score = calculate_compliance_score(remote_class, geo_class)
        return {"compliance_status": "review", "compliance_score": score}

    # Everything else
    score = calculate_compliance_score(remote_class, geo_class)
    return {"compliance_status": "unknown", "compliance_score": score}
