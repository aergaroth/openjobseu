import pytest

from app.domain.classification.enums import ComplianceStatus, GeoClass, RemoteClass
from app.workers.compliance_resolver import calculate_compliance_score, resolve_compliance


@pytest.mark.parametrize(
    ("remote_class", "geo_class"),
    [
        (RemoteClass.NON_REMOTE.value, GeoClass.EU_MEMBER_STATE.value),
        ("office_first", GeoClass.EU_MEMBER_STATE.value),
        ("hybrid", GeoClass.UK.value),
    ],
)
def test_non_remote_variants_are_hard_rejected(remote_class: str, geo_class: str):
    result = resolve_compliance(remote_class, geo_class)
    assert result["compliance_status"] == ComplianceStatus.REJECTED.value
    assert result["compliance_score"] == 0


@pytest.mark.parametrize("geo_class", [GeoClass.NON_EU.value, "non_eu_restricted"])
def test_non_eu_variants_are_hard_rejected(geo_class: str):
    result = resolve_compliance(RemoteClass.REMOTE_ONLY.value, geo_class)
    assert result["compliance_status"] == ComplianceStatus.REJECTED.value
    assert result["compliance_score"] == 0


@pytest.mark.parametrize(
    "geo_class",
    [
        GeoClass.EU_MEMBER_STATE.value,
        GeoClass.EU_EXPLICIT.value,
        GeoClass.EU_REGION.value,
        GeoClass.UK.value,
        "eog",
    ],
)
def test_remote_only_on_eu_eligible_geo_is_approved(geo_class: str):
    result = resolve_compliance(RemoteClass.REMOTE_ONLY.value, geo_class)
    assert result["compliance_status"] == ComplianceStatus.APPROVED.value
    assert result["compliance_score"] == 100


@pytest.mark.parametrize(
    "remote_class",
    ["remote_but_geo_restricted", RemoteClass.REMOTE_REGION_LOCKED.value],
)
@pytest.mark.parametrize(
    "geo_class",
    [
        GeoClass.EU_MEMBER_STATE.value,
        GeoClass.EU_EXPLICIT.value,
        GeoClass.EU_REGION.value,
        GeoClass.UK.value,
    ],
)
def test_region_locked_remote_on_eu_eligible_geo_is_approved(remote_class: str, geo_class: str):
    result = resolve_compliance(remote_class, geo_class)
    assert result["compliance_status"] == ComplianceStatus.APPROVED.value
    assert result["compliance_score"] == 90


@pytest.mark.parametrize(
    "geo_class",
    [
        GeoClass.EU_MEMBER_STATE.value,
        GeoClass.EU_EXPLICIT.value,
        GeoClass.EU_REGION.value,
        GeoClass.UK.value,
    ],
)
def test_remote_optional_on_eu_eligible_geo_is_review(geo_class: str):
    result = resolve_compliance(RemoteClass.REMOTE_OPTIONAL.value, geo_class)
    assert result["compliance_status"] == ComplianceStatus.REVIEW.value
    assert result["compliance_score"] == 60


@pytest.mark.parametrize(
    "geo_class",
    [
        GeoClass.EU_MEMBER_STATE.value,
        GeoClass.EU_EXPLICIT.value,
        GeoClass.EU_REGION.value,
        GeoClass.UK.value,
    ],
)
def test_unknown_remote_on_eu_eligible_geo_is_review(geo_class: str):
    result = resolve_compliance(RemoteClass.UNKNOWN.value, geo_class)
    assert result["compliance_status"] == ComplianceStatus.REVIEW.value
    assert result["compliance_score"] == 55


@pytest.mark.parametrize(
    "geo_class",
    ["worldwide", "global", "eu_friendly", GeoClass.UNKNOWN.value, "unexpected"],
)
def test_unknown_geo_variants_fall_back_to_rejected(geo_class: str):
    result = resolve_compliance(RemoteClass.REMOTE_ONLY.value, geo_class)
    assert result["compliance_status"] == ComplianceStatus.REJECTED.value
    assert result["compliance_score"] == 20


def test_calculate_compliance_score_returns_score_only():
    assert calculate_compliance_score(RemoteClass.REMOTE_ONLY.value, GeoClass.EU_MEMBER_STATE.value) == 100
    assert calculate_compliance_score(RemoteClass.REMOTE_ONLY.value, GeoClass.UNKNOWN.value) == 20
