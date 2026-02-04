from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_jobs_feed_returns_200():
    r = client.get("/jobs/feed")
    assert r.status_code == 200


def test_jobs_feed_has_expected_shape():
    r = client.get("/jobs/feed")
    data = r.json()

    assert "meta" in data
    assert "jobs" in data

    meta = data["meta"]
    assert meta["status"] == "visible"
    assert meta["version"] == "v1"
    assert isinstance(meta["count"], int)
    assert meta["limit"] == 200


def test_jobs_feed_items_have_stable_fields():
    r = client.get("/jobs/feed")
    jobs = r.json()["jobs"]

    if not jobs:
        return  # empty feed is valid

    job = jobs[0]

    expected_fields = {
        "id",
        "title",
        "company",
        "remote_scope",
        "source",
        "url",
        "first_seen_at",
        "status",
    }

    assert set(job.keys()) == expected_fields


def test_jobs_feed_status_is_visible_only():
    r = client.get("/jobs/feed")
    jobs = r.json()["jobs"]

    for job in jobs:
        assert job["status"] in ("new", "active")


def test_jobs_feed_cache_header_present():
    r = client.get("/jobs/feed")
    assert "cache-control" in r.headers
    assert "max-age=300" in r.headers["cache-control"]