from app.workers.normalization.remoteok import normalize_remoteok_job


def test_remoteok_normalization_happy_path():
    raw = {
        "id": 123,
        "position": "Senior Backend Engineer",
        "company": "Acme Corp",
        "description": "We are hiring!",
        "location": "Europe",
        "url": "https://remoteok.com/remote-jobs/123",
        "date": "2026-02-05T14:00:02+00:00",
    }

    job = normalize_remoteok_job(raw)

    assert job is not None
    assert job["job_id"] == "remoteok:123"
    assert job["source"] == "remoteok"
    assert job["source_job_id"] == "123"
    assert job["title"] == "Senior Backend Engineer"
    assert job["company_name"] == "Acme Corp"
    assert job["remote"] is True
    assert job["remote_scope"] == "EU-wide"
    assert job["status"] == "new"
    assert job["first_seen_at"] == "2026-02-05T14:00:02+00:00"


def test_remoteok_normalization_worldwide_scope():
    raw = {
        "id": 456,
        "position": "DevOps Engineer",
        "company": "Globex",
        "description": "Remote role",
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/456",
        "epoch": 1738764000,
    }

    job = normalize_remoteok_job(raw)

    assert job is not None
    assert job["remote_scope"] == "worldwide"


def test_remoteok_skips_job_without_required_fields():
    raw = {
        "id": 789,
        # missing position
        "company": "Broken Inc",
        "url": "https://remoteok.com/remote-jobs/789",
    }

    job = normalize_remoteok_job(raw)

    assert job is None


def test_remoteok_uses_epoch_when_date_missing():
    raw = {
        "id": 999,
        "position": "QA Engineer",
        "company": "Testers United",
        "location": "EU",
        "url": "https://remoteok.com/remote-jobs/999",
        "epoch": 1738764000,
    }

    job = normalize_remoteok_job(raw)

    assert job is not None
    assert job["first_seen_at"].endswith("+00:00")
