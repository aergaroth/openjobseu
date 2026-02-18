from app.workers.compliance_resolver import resolve_compliance


def test_rejected_non_remote():
    result = resolve_compliance("non_remote", "eu_explicit")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


def test_rejected_non_eu():
    result = resolve_compliance("remote_only", "non_eu")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


def test_approved_remote_eu():
    result = resolve_compliance("remote_only", "eu_explicit")
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] > 0


def test_review_unknown_remote():
    result = resolve_compliance("unknown", "eu_friendly")
    assert result["compliance_status"] == "review"
