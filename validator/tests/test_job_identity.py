from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
    compute_schema_hash,
    normalize,
)


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Senior   Backend \n Engineer  ") == "senior backend engineer"


def test_compute_job_uid_is_stable_for_equivalent_text():
    uid_a = compute_job_uid(
        "company-1",
        " Senior Backend Engineer ",
        " Remote   EU ",
    )
    uid_b = compute_job_uid(
        "company-1",
        "senior backend engineer",
        "remote eu",
    )
    assert uid_a == uid_b


def test_compute_job_fingerprint_uses_first_500_chars():
    prefix = "A" * 500
    fingerprint_a = compute_job_fingerprint(prefix + "X")
    fingerprint_b = compute_job_fingerprint(prefix + "Y")
    assert fingerprint_a == fingerprint_b


def test_compute_job_fingerprint_includes_identity_context():
    description = "Same description body"
    fingerprint_a = compute_job_fingerprint(
        description,
        title="Backend Engineer",
        location="Europe",
        company_id="company-1",
        company_name="Acme",
    )
    fingerprint_b = compute_job_fingerprint(
        description,
        title="Backend Engineer",
        location="Europe",
        company_id="company-2",
        company_name="Acme",
    )
    assert fingerprint_a != fingerprint_b


def test_compute_schema_hash_uses_schema_not_values():
    payload_a = {
        "id": 1,
        "meta": {
            "active": True,
            "tags": ["engineering", "python"],
        },
    }
    payload_b = {
        "meta": {
            "tags": ["backend", "jobs"],
            "active": False,
        },
        "id": 999,
    }
    payload_c = {
        "id": "999",
        "meta": {
            "active": False,
            "tags": ["backend", "jobs"],
        },
    }

    assert compute_schema_hash(payload_a) == compute_schema_hash(payload_b)
    assert compute_schema_hash(payload_a) != compute_schema_hash(payload_c)
