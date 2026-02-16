from app.workers.policy.v2.remote_classifier import classify_remote_model


def test_detects_remote_only():
    result = classify_remote_model(
        "Backend Engineer",
        "This is a fully remote role. 100% remote.",
    )
    assert result["remote_model"] == "remote_only"


def test_detects_hybrid():
    result = classify_remote_model(
        "Software Engineer",
        "Hybrid role, 3 days in office.",
    )
    assert result["remote_model"] == "hybrid"


def test_detects_office_first():
    result = classify_remote_model(
        "Engineer",
        "We are an office-first company and do not offer remote-only roles.",
    )
    assert result["remote_model"] == "office_first"


def test_detects_remote_but_geo_restricted():
    result = classify_remote_model(
        "Senior PM",
        "Fully remote but must be based in the US.",
    )
    assert result["remote_model"] == "remote_but_geo_restricted"


def test_unknown_when_no_signal():
    result = classify_remote_model(
        "Account Manager",
        "Great opportunity in our growing company.",
    )
    assert result["remote_model"] == "unknown"
