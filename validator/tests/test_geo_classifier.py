from app.domain.classification.enums import GeoClass
from app.domain.compliance.classifiers.geo import classify_geo_scope, classify_geo_v3
from app.domain.compliance.classifiers.remote import classify_remote_v3
from app.domain.compliance.engine import apply_policy


def test_geo_scope_eu_explicit():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote within European Union only",
    )
    assert result["geo_class"] == GeoClass.EU_EXPLICIT.value


def test_geo_scope_eu_member_state():
    result = classify_geo_scope(
        "Backend Engineer",
        "This role is remote in Poland",
    )
    assert result["geo_class"] == GeoClass.EU_MEMBER_STATE.value


def test_geo_scope_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote - USA only",
    )
    assert result["geo_class"] == GeoClass.NON_EU.value


def test_geo_scope_us_hard_phrases_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote US, must live in the US, US-based only",
    )
    assert result["geo_class"] == GeoClass.NON_EU.value


def test_geo_scope_canada_hard_signal_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote in Canada only",
    )
    assert result["geo_class"] == GeoClass.NON_EU.value


def test_geo_scope_apac_signal_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Open to APAC candidates",
    )
    assert result["geo_class"] == GeoClass.NON_EU.value


def test_geo_scope_us_states_three_abbreviations_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Applicants can be based in CA, NY, TX",
    )
    assert result["geo_class"] == GeoClass.NON_EU.value


def test_geo_scope_worldwide_is_unknown():
    result = classify_geo_scope(
        "Backend Engineer",
        "Fully remote worldwide",
    )
    assert result["geo_class"] == GeoClass.UNKNOWN.value


def test_geo_scope_uk():
    result = classify_geo_scope(
        "Backend Engineer",
        "London office",
    )
    assert result["geo_class"] == GeoClass.UK.value


def test_geo_scope_unknown():
    result = classify_geo_scope(
        "Backend Engineer",
        "Some vague description without geo info",
    )
    assert result["geo_class"] == GeoClass.UNKNOWN.value


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


def test_geo_v3_marks_remote_us_scope_as_non_eu_even_with_poland_in_description():
    description = (
        "You will also serve as our Poland market lead and shape Poland market strategy."
    )
    title = "Talent Brand Creative & Campaigns Lead"
    remote_scope = "Remote - US: Select locations"

    geo = classify_geo_v3(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )
    remote = classify_remote_v3(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )
    job, reason = apply_policy(
        {
            "title": title,
            "description": description,
            "remote_scope": remote_scope,
        },
        source="employer_ing",
    )

    assert geo["geo_class"] == GeoClass.NON_EU
    assert reason is None
    assert remote["remote_model"] is not None
    assert job is not None
    assert job["_compliance"]["geo_class"] == GeoClass.NON_EU
