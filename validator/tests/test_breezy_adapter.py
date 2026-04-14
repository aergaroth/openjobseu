import pytest
from unittest.mock import MagicMock

from app.adapters.ats.breezy import BreezyAdapter


def test_breezy_fetch_invalid_payload(monkeypatch):
    adapter = BreezyAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"not": "a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(ValueError, match="did not return a list"):
        adapter.fetch({"ats_slug": "acme"})


def test_breezy_fetch_only_published_jobs(monkeypatch):
    adapter = BreezyAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"_id": "1", "state": "published", "published_date": "2024-01-02"},
        {"_id": "2", "state": "draft", "published_date": "2024-01-01"},
    ]
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    jobs = adapter.fetch({"ats_slug": "acme"})
    assert len(jobs) == 1
    assert jobs[0]["_id"] == "1"
    assert jobs[0]["_ats_slug"] == "acme"


def test_breezy_probe_jobs_returns_company_name(monkeypatch):
    adapter = BreezyAdapter()
    monkeypatch.setattr(
        adapter,
        "fetch",
        lambda company, **kw: [
            {
                "_id": "1",
                "name": "Backend Engineer",
                "published_date": "2024-03-01",
                "location": {"name": "Remote", "is_remote": True},
                "company": {"name": "Acme Ltd"},
            }
        ],
    )

    result = adapter.probe_jobs("acme-slug")
    assert result["jobs_total"] == 1
    assert result["remote_hits"] == 1
    assert result["recent_job_at"] == "2024-03-01"
    assert result["company_name"] == "Acme Ltd"


def test_breezy_normalize_prefers_company_from_payload():
    adapter = BreezyAdapter()
    raw_job = {
        "_ats_slug": "acme-slug",
        "_id": "123",
        "name": "Backend Engineer",
        "url": "https://acme-slug.breezy.hr/p/123",
        "description": "<p>Hello</p>",
        "location": {"name": "Warsaw, Poland", "is_remote": False},
        "company": {"name": "Acme Holdings"},
    }

    result = adapter.normalize(raw_job)
    assert result is not None
    assert result["company_name"] == "Acme Holdings"


def test_breezy_normalize_company_name_fallback_to_slug():
    adapter = BreezyAdapter()
    raw_job = {
        "_ats_slug": "my-company",
        "_id": "321",
        "name": "Dev",
        "url": "https://my-company.breezy.hr/p/321",
    }

    result = adapter.normalize(raw_job)
    assert result is not None
    assert result["company_name"] == "My Company"
