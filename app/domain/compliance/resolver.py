from app.domain.jobs.constants import EU_ELIGIBLE_GEO_CLASSES
from app.domain.compliance.classifiers.enums import ComplianceStatus
from app.domain.jobs.enums import GeoClass, RemoteClass
from app.domain.jobs.mappers import normalize_geo_class, normalize_remote_class


def _resolve_score_and_status(
    remote_class: str | None,
    geo_class: str | None,
) -> tuple[int, ComplianceStatus]:
    remote = normalize_remote_class(remote_class)
    geo = normalize_geo_class(geo_class)

    if remote == RemoteClass.NON_REMOTE:
        return 0, ComplianceStatus.REJECTED

    if geo == GeoClass.NON_EU:
        return 0, ComplianceStatus.REJECTED

    if remote == RemoteClass.REMOTE_ONLY and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 100, ComplianceStatus.APPROVED

    if remote == RemoteClass.REMOTE_REGION_LOCKED and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 90, ComplianceStatus.APPROVED

    if remote == RemoteClass.REMOTE_OPTIONAL and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 60, ComplianceStatus.REVIEW

    if remote == RemoteClass.UNKNOWN and geo in EU_ELIGIBLE_GEO_CLASSES:
        return 55, ComplianceStatus.REVIEW

    return 20, ComplianceStatus.REJECTED


def resolve(remote_class: str | None, geo_class: str | None) -> dict:
    score, status = _resolve_score_and_status(remote_class, geo_class)
    return {
        "compliance_status": status.value,
        "compliance_score": score,
    }


def resolve_compliance(remote_class: str | None, geo_class: str | None) -> dict:
    return resolve(remote_class, geo_class)
