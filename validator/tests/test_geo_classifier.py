from app.domain.jobs.enums import GeoClass
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


def test_geo_v3_detects_city_in_remote_scope():
    result = classify_geo_v3(
        title="Data Scientist",
        description="",
        remote_scope="Remote - Berlin",
    )

    assert result["geo_class"] == GeoClass.EU_MEMBER_STATE
    assert result["reason"] == "explicit_country"


def test_geo_v3_detects_city_in_title():
    result = classify_geo_v3(
        title="Frontend Engineer - Warsaw",
        description="",
        remote_scope="",
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
        title="Senior Backend Engineer",
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
    description = "You will also serve as our Poland market lead and shape Poland market strategy."
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


def test_geo_v3_mixed_region_resolves_to_eu_region():
    result = classify_geo_v3(
        title="Software Engineer - US & EMEA",
        description="",
        remote_scope="US & EMEA",
    )
    assert result["geo_class"] == GeoClass.EU_REGION
    assert result["reason"] == "mixed_region"


def test_geo_v3_non_eu_scope_title_phrase_overrides_emea_mixed_region():
    result = classify_geo_v3(
        title="HR Experience Specialist | Israel",
        description="",
        remote_scope="EMEA",
    )
    assert result["geo_class"] == GeoClass.NON_EU
    assert result["reason"] == "israel"


def test_geo_v3_apac_scope_not_eu():
    # Regression: jobs with APAC/Oceania/LatAm scopes were incorrectly approved because
    # those countries were missing from NON_EU_SCOPE_TITLE_PHRASES.
    apac_cases = [
        ("auckland, auckland, new zealand", "Senior Staff Software Engineer"),
        ("manila, manila, philippines", "People and Culture Coordinator"),
        ("sydney, new south wales, australia", "Account Executive"),
        ("remote, india, apac", "Solution Architect"),
        ("mexico city, mexico", "iOS Engineer"),
    ]
    for scope, title in apac_cases:
        result = classify_geo_v3(title=title, description="", remote_scope=scope)
        assert result["geo_class"] == GeoClass.NON_EU, f"Expected NON_EU for scope='{scope}', got {result['geo_class']}"

    # EMEA title + India/APAC scope → NON_EU (scope phrase wins via non_eu_scope_title_phrase_hit)
    result = classify_geo_v3(
        title="Solution Architect, Networking - EMEA Hours",
        description="",
        remote_scope="remote, india, apac",
    )
    assert result["geo_class"] == GeoClass.NON_EU


def test_geo_v3_europe_in_boilerplate_with_multi_region_context_is_not_eu():
    # Regression: company boilerplate like "offices in north america, europe, and asia pacific"
    # was triggering eu_region because the description-level "europe" had no conflict guard.
    # The guard applies only when broad multi-region signals ("north america", "americas",
    # "asia pacific", "apac") are present — not for single-region phrases like "latam",
    # which may appear as a direct candidate location alongside "europe".
    lightspeed_boilerplate = (
        "Lightspeed is listed on the nasdaq (lspd) and toronto stock exchange (tsx: lspd). "
        "With teams across north america, europe, and asia pacific, the company serves retail, "
        "hospitality, and golf businesses worldwide."
    )
    # NZ scope is already caught by scope-level detection (new zealand in NON_EU_SCOPE_TITLE_PHRASES)
    result = classify_geo_v3(
        title="Senior Staff Software Engineer",
        description=lightspeed_boilerplate,
        remote_scope="auckland, auckland, new zealand",
    )
    assert result["geo_class"] == GeoClass.NON_EU

    # Scope-neutral (just "remote") with "north america" + "europe" in boilerplate → not EU-targeted
    result = classify_geo_v3(
        title="Software Engineer",
        description=lightspeed_boilerplate,
        remote_scope="remote",
    )
    assert result["geo_class"] != GeoClass.EU_REGION
    assert result["geo_class"] != GeoClass.EU_MEMBER_STATE


def test_geo_v3_latam_or_europe_direct_scope_stays_eu():
    # "latam or europe" as a direct candidate location statement (not company boilerplate)
    # must not be blocked by the multi-region conflict guard — the job IS EU-eligible.
    result = classify_geo_v3(
        title="Senior Software Engineer",
        description="This role can be based in latam or europe. We cannot hire in the usa for this position.",
        remote_scope="remote",
    )
    assert result["geo_class"] in (GeoClass.EU_REGION, GeoClass.EU_MEMBER_STATE)


def test_geo_v3_global_role_emea_and_apac_in_description_is_not_eu():
    # Regression: global IT/ops roles mentioning EMEA alongside APAC/Americas in the description
    # (e.g. SAM, IT Program Manager) were incorrectly classified as EU_REGION.
    # "EMEA" in a job description that also mentions other non-EU regions means the role
    # is globally scoped, not EU-targeted — candidate location is not restricted to EU.
    description = (
        "You will manage software asset lifecycles across all regions including EMEA, APAC, "
        "and the Americas. Responsibilities include license compliance globally."
    )
    result = classify_geo_v3(
        title="Sr IT Project/Program Manager - SAM",
        description=description,
        remote_scope="remote",
    )
    assert result["geo_class"] != GeoClass.EU_REGION
    assert result["geo_class"] != GeoClass.EU_MEMBER_STATE

    job, _ = apply_policy(
        {"title": "Sr IT Project/Program Manager - SAM", "description": description, "remote_scope": "remote"},
        source="employer_ing",
    )
    assert job["_compliance"]["compliance_score"] < 80
