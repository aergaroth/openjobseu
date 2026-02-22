from app.workers.compliance_resolver import resolve_compliance


def test_rejected_non_remote():
    result = resolve_compliance("non_remote", "eu_member_state")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


def test_rejected_non_eu():
    result = resolve_compliance("remote_only", "non_eu")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


def test_rejected_non_eu_alias():
    result = resolve_compliance("remote_only", "non_eu_restricted")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 0


def test_approved_remote_only_eu_member_state():
    result = resolve_compliance("remote_only", "eu_member_state")
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 100


def test_approved_remote_only_eu_region():
    result = resolve_compliance("remote_only", "eu_region")
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 90


def test_approved_remote_only_eu_explicit_alias():
    result = resolve_compliance("remote_only", "eu_explicit")
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 90


def test_approved_remote_only_uk():
    result = resolve_compliance("remote_only", "uk")
    assert result["compliance_status"] == "approved"
    assert result["compliance_score"] == 85


def test_worldwide_alias_is_unknown_and_rejected():
    result = resolve_compliance("remote_only", "worldwide")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 20


def test_review_remote_geo_restricted_eu_member_state():
    result = resolve_compliance("remote_but_geo_restricted", "eu_member_state")
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 70


def test_review_remote_geo_restricted_eu_region():
    result = resolve_compliance("remote_but_geo_restricted", "eu_region")
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 65


def test_worldwide_alias_rejected_for_geo_restricted_remote():
    result = resolve_compliance("remote_but_geo_restricted", "worldwide")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 20


def test_review_unknown_remote_eu_member_state():
    result = resolve_compliance("unknown", "eu_member_state")
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 60


def test_review_unknown_remote_eu_region():
    result = resolve_compliance("unknown", "eu_region")
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 55


def test_review_unknown_remote_uk():
    result = resolve_compliance("unknown", "uk")
    assert result["compliance_status"] == "review"
    assert result["compliance_score"] == 55


def test_worldwide_alias_rejected_for_unknown_remote():
    result = resolve_compliance("unknown", "worldwide")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 20


def test_default_fallback_rejected_with_score_20():
    result = resolve_compliance("remote_only", "unknown")
    assert result["compliance_status"] == "rejected"
    assert result["compliance_score"] == 20
