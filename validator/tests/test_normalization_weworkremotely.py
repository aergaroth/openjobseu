from app.workers.normalization.weworkremotely import (
    normalize_weworkremotely_job,
)


def test_weworkremotely_normalization_happy_path():
    raw = {
        "title": "Acme Corp: Senior Backend Engineer",
        "link": "https://weworkremotely.com/remote-jobs/123",
        "id": "wwr-123",
        "summary": "Great job opportunity",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["job_id"] == "weworkremotely:wwr-123"
    assert job["source"] == "weworkremotely"
    assert job["source_job_id"] == "wwr-123"
    assert job["title"] == "Senior Backend Engineer"
    assert job["company_name"] == "Acme Corp"
    assert job["remote_source_flag"] is True
    assert job["remote_scope"] == "EU-wide"
    assert job["status"] == "new"
    assert job["source_url"] == raw["link"]
    assert job["description"] == "Great job opportunity"
    assert job["first_seen_at"].endswith("+00:00")


def test_weworkremotely_normalization_without_company_prefix():
    raw = {
        "title": "Backend Engineer",
        "link": "https://weworkremotely.com/remote-jobs/456",
        "id": "wwr-456",
        "summary": "Remote role",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["title"] == "Backend Engineer"
    assert job["company_name"] == "unknown"


def test_weworkremotely_skips_job_without_required_fields():
    raw = {
        "title": "",
        "link": None,
    }

    job = normalize_weworkremotely_job(raw)

    assert job is None


def test_weworkremotely_company_heuristic_is_safe():
    raw = {
        "title": "X: Y: Z Engineer",
        "link": "https://weworkremotely.com/remote-jobs/789",
        "id": "wwr-789",
        "summary": "Complex title",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    # too short company name -> heuristic should not work
    assert job["company_name"] == "unknown"
    assert job["title"] == "X: Y: Z Engineer"


def test_weworkremotely_company_heuristic_ignores_url_like_prefix():
    raw = {
        "title": "https://weworkremotely.com/remote-jobs/acme-backend-engineer: Backend Engineer",
        "link": "https://weworkremotely.com/remote-jobs/acme-backend-engineer",
        "id": "wwr-999",
        "summary": "Role",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["company_name"] == "unknown"
    assert job["title"] == raw["title"]


def test_weworkremotely_uses_source_published_date_when_present():
    raw = {
        "title": "Acme Corp: Senior Backend Engineer",
        "link": "https://weworkremotely.com/remote-jobs/321",
        "id": "wwr-321",
        "summary": "Great role",
        "published": "Thu, 06 Feb 2026 14:30:00 +0000",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["first_seen_at"] == "2026-02-06T14:30:00+00:00"


def test_weworkremotely_normalization_cleans_url():
    raw = {
        "title": "Acme Corp: Senior Backend Engineer",
        "link": " https://weworkremotely.com/remote-jobs/654?utm_campaign=rss&src=feed#content ",
        "id": "wwr-654",
        "summary": "Great role",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["source_url"] == "https://weworkremotely.com/remote-jobs/654?src=feed"


def test_weworkremotely_uses_slug_when_raw_id_is_url():
    raw = {
        "title": "Acme Corp: Senior Backend Engineer",
        "link": "https://weworkremotely.com/remote-jobs/acme-backend-engineer",
        "id": "https://weworkremotely.com/remote-jobs/acme-backend-engineer",
        "summary": "Great role",
    }

    job = normalize_weworkremotely_job(raw)

    assert job is not None
    assert job["source_job_id"] == "acme-backend-engineer"
    assert job["job_id"] == "weworkremotely:acme-backend-engineer"
