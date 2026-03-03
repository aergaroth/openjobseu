from typing import Dict
from app.domain.classification.enums import (
    RemoteClass,
    GeoClass,
    ComplianceStatus,
)
from app.domain.classification.constants import EU_ELIGIBLE_GEO_CLASSES
from app.domain.classification.mappers import (
    normalize_geo_class,
    normalize_remote_class,
)


def _resolve_score_and_status(
    remote_class: str | None,
    geo_class: str | None,
) -> tuple[int, ComplianceStatus]:

    remote = normalize_remote_class(remote_class)
    geo = normalize_geo_class(geo_class)

    # Hard reject
    if remote == RemoteClass.NON_REMOTE:
        return 0, ComplianceStatus.REJECTED

    if geo == GeoClass.NON_EU:
        return 0, ComplianceStatus.REJECTED

    # Fully remote
    if remote == RemoteClass.REMOTE_ONLY and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 100, ComplianceStatus.APPROVED

    # Region locked
    if remote == RemoteClass.REMOTE_REGION_LOCKED and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 90, ComplianceStatus.APPROVED

    # Optional
    if remote == RemoteClass.REMOTE_OPTIONAL and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 60, ComplianceStatus.REVIEW

    # Unknown remote but EU geo
    if remote == RemoteClass.UNKNOWN and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 55, ComplianceStatus.REVIEW

    return 20, ComplianceStatus.REJECTED


def calculate_compliance_score(remote_class: str | None, geo_class: str | None) -> int:
    score, _status = _resolve_score_and_status(remote_class, geo_class)
    return score


def resolve_compliance(remote_class: str | None, geo_class: str | None) -> Dict:
    score, status = _resolve_score_and_status(remote_class, geo_class)

    return {
        "compliance_status": status.value,
        "compliance_score": score,
    }
