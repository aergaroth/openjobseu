from app.workers.policy.v2.geo_classifier import classify_geo_scope


def test_eu_explicit():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote within European Union only",
    )
    assert result["geo_class"] == "eu_explicit"


def test_eu_member_state():
    result = classify_geo_scope(
        "Backend Engineer",
        "This role is remote in Poland",
    )
    assert result["geo_class"] == "eu_member_state"


def test_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote – USA only",
    )
    assert result["geo_class"] == "non_eu"


def test_us_hard_phrases_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote US, must live in the US, US-based only",
    )
    assert result["geo_class"] == "non_eu"


def test_canada_hard_signal_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Remote in Canada only",
    )
    assert result["geo_class"] == "non_eu"


def test_apac_signal_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Open to APAC candidates",
    )
    assert result["geo_class"] == "non_eu"


def test_us_states_three_abbreviations_non_eu():
    result = classify_geo_scope(
        "Backend Engineer",
        "Applicants can be based in CA, NY, TX",
    )
    assert result["geo_class"] == "non_eu"


def test_worldwide_is_unknown():
    result = classify_geo_scope(
        "Backend Engineer",
        "Fully remote worldwide",
    )
    assert result["geo_class"] == "unknown"


def test_uk():
    result = classify_geo_scope(
        "Backend Engineer",
        "London office",
    )
    assert result["geo_class"] == "uk"


def test_unknown():
    result = classify_geo_scope(
        "Backend Engineer",
        "Some vague description without geo info",
    )
    assert result["geo_class"] == "unknown"
