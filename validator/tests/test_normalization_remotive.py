from app.workers.normalization.remotive import normalize_remotive_job


def test_remotive_normalization_happy_path():
    raw = {
        "id": 123,
        "title": "Backend Engineer",
        "company_name": "Acme Corp",
        "description": "Great job",
        "url": "https://remotive.com/remote-jobs/123",
        "candidate_required_location": "Europe",
        "publication_date": "2026-02-05T14:00:02+00:00",
    }

    job = normalize_remotive_job(raw)

    assert job is not None
    assert job["source"] == "remotive"
    assert job["source_job_id"] == "123"
    assert job["title"] == "Backend Engineer"
    assert job["company_name"] == "Acme Corp"
    assert job["remote"] is True
    assert job["remote_scope"] == "Europe"
    assert job["status"] == "new"
    assert job["source_url"] == raw["url"]


def test_remotive_normalization_skips_non_eu_jobs():
    raw = {
        "id": 124,
        "title": "Engineer",
        "company_name": "ACME",
        "description": "Job",
        "url": "https://remotive.com/remote-jobs/124",
        "candidate_required_location": "USA",
    }

    job = normalize_remotive_job(raw)

    assert job is None


def test_remotive_normalization_handles_worldwide_as_valid():
    raw = {
        "id": 125,
        "title": "DevOps Engineer",
        "company_name": "Globex",
        "description": "Infra stuff",
        "url": "https://remotive.com/remote-jobs/125",
        "candidate_required_location": "Worldwide",
    }

    job = normalize_remotive_job(raw)

    assert job is not None
    assert job["remote_scope"] == "Worldwide"


def test_remotive_normalization_skips_missing_required_fields():
    raw = {
        "id": 126,
        "company_name": "Broken Inc",
        # brak title, url, description
    }

    job = normalize_remotive_job(raw)

    assert job is None


def test_remotive_job_id_is_stable_string():
    raw = {
        "id": 999,
        "title": "Engineer",
        "company_name": "Test",
        "description": "Test",
        "url": "https://remotive.com/remote-jobs/999",
        "candidate_required_location": "Europe",
    }

    job = normalize_remotive_job(raw)

    assert job["job_id"] == "remotive:999"
    assert isinstance(job["job_id"], str)
