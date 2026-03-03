from app.domain.classification.enums import GeoClass
from app.workers.policy.v3.geo_v3 import classify_geo_v3


def test_geo_v3_uses_country_from_remote_scope_first():
    result = classify_geo_v3(
        title="Senior Backend Engineer",
        description="Localization: United States",
        remote_scope="Poland",
    )

    assert result["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert result["reason"] == "explicit_country"


def test_geo_v3_falls_back_to_localization_section_in_description():
    description = """
Overview
Work from anywhere.

Localization
Germany, Poland

Benefits
Private healthcare.
"""
    result = classify_geo_v3(
        title="Senior Backend Engineer",
        description=description,
        remote_scope="",
    )

    assert result["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert result["reason"] in {"germany", "poland"}


def test_geo_v3_does_not_set_eu_member_state_from_general_text():
    description = """
Overview
Our team has members in Poland and Germany.

Responsibilities
Build APIs and integrations.
"""
    result = classify_geo_v3(
        title="Senior Backend Engineer in Poland",
        description=description,
        remote_scope="",
    )

    assert result["geo_class"] != GeoClass.EU_MEMBER_STATE


def test_geo_v3_ignores_two_letter_aliases_in_localization_fallback():
    result = classify_geo_v3(
        title="Senior Backend Engineer",
        description="Localization: DE, FR, NL",
        remote_scope="",
    )

    assert result["geo_class"] != GeoClass.EU_MEMBER_STATE
