from app.workers.normalization.cleaning import clean_description
from app.workers.policy.v1 import evaluate_policy


def test_remoteok_spam_removed():
    raw = (
        "Valid content.\n\n"
        "Please mention the word **TEST** and tag ABC.\n"
        "This is a beta feature to avoid spam applicants."
    )

    cleaned = clean_description(raw, source="remoteok")

    assert "Please mention the word" not in cleaned
    assert cleaned.strip() == "Valid content."


def test_remoteok_html_and_whitespace():
    raw = "Hello<br/><br/><b>World</b>"

    cleaned = clean_description(raw, source="remoteok")

    assert "<" not in cleaned
    assert "World" in cleaned


def test_policy_rejects_us_only():
    job = {
        "title": "Senior PM",
        "description": "100% remote but must be based in the US",
    }

    assert evaluate_policy(job) == (False, "geo_restriction")


def test_policy_rejects_non_remote():
    job = {
        "title": "Senior PM (hybrid)",
        "description": "Great role",
    }

    assert evaluate_policy(job) == (False, "non_remote")


def test_policy_accepts_clean_remote_role():
    job = {
        "title": "Senior Backend Engineer",
        "description": "Fully remote role across Europe",
    }

    assert evaluate_policy(job) == (True, None)
