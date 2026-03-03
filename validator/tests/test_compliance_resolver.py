import pytest

from app.workers.compliance_resolver import calculate_compliance_score, resolve_compliance


@pytest.mark.parametrize(
    ("remote_class", "geo_class"),
    [
        ("non_remote", "eu_member_state"),
        ("office_first", "eu_member_state"),
        ("hybrid", "uk"),
    ],
)
def test_non_remote_variants_are_hard_rejected(remote_class: str, geo_class: str):
    result = resolve_compliance(remote_class, geo_class)
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


@pytest.mark.parametrize("geo_class", ["non_eu", "non_eu_restricted"])
def test_non_eu_variants_are_hard_rejected(geo_class: str):
    result = resolve_compliance("remote_only", geo_class)
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


@pytest.mark.parametrize(
    "geo_class",
    [
        "eu_member_state",
        "eu_explicit",
        "eu_region",
        "uk",
        "eog",
    ],
)
def test_remote_only_on_eu_eligible_geo_is_approved(geo_class: str):
    result = resolve_compliance("remote_only", geo_class)
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 100


@pytest.mark.parametrize("remote_class", ["remote_but_geo_restricted", "remote_region_locked"])
@pytest.mark.parametrize("geo_class", ["eu_member_state", "eu_explicit", "eu_region", "uk"])
def test_region_locked_remote_on_eu_eligible_geo_is_approved(remote_class: str, geo_class: str):
    result = resolve_compliance(remote_class, geo_class)
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 90


@pytest.mark.parametrize("geo_class", ["eu_member_state", "eu_explicit", "eu_region", "uk"])
def test_remote_optional_on_eu_eligible_geo_is_review(geo_class: str):
    result = resolve_compliance("remote_optional", geo_class)
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 60


@pytest.mark.parametrize("geo_class", ["eu_member_state", "eu_explicit", "eu_region", "uk"])
def test_unknown_remote_on_eu_eligible_geo_is_review(geo_class: str):
    result = resolve_compliance("unknown", geo_class)
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 55


@pytest.mark.parametrize("geo_class", ["worldwide", "global", "eu_friendly", "unknown", "unexpected"])
def test_unknown_geo_variants_fall_back_to_rejected(geo_class: str):
    result = resolve_compliance("remote_only", geo_class)
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 20


def test_calculate_compliance_score_returns_score_only():
    assert calculate_compliance_score("remote_only", "eu_member_state") == 100
    assert calculate_compliance_score("remote_only", "unknown") == 20
