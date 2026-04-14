import pytest
from unittest.mock import MagicMock

from app.adapters.ats.traffit import TraffitAdapter


def test_traffit_fetch_invalid_payload(monkeypatch):
    adapter = TraffitAdapter()
    mock_resp = MagicMock()
    mock_resp.headers = {}
    mock_resp.json.return_value = {"not": "a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(ValueError, match="did not return a list"):
        adapter.fetch({"ats_slug": "acme"})


def test_traffit_fetch_success_single_page(monkeypatch):
    adapter = TraffitAdapter()
    mock_resp = MagicMock()
    mock_resp.headers = {"X-Result-Total-Pages": "1"}
    mock_resp.json.return_value = [{"id": 1, "valid_start": "2023-01-01 00:00:00"}]
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    jobs = adapter.fetch({"ats_slug": "acme"})
    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "acme"
    assert jobs[0]["_incremental_at"] == "2023-01-01 00:00:00"


def test_traffit_fetch_paginates_without_total_pages_header(monkeypatch):
    adapter = TraffitAdapter()
    calls = {"n": 0}

    def fake_get(*a, **kw):
        calls["n"] += 1
        mock_resp = MagicMock()
        mock_resp.headers = {}
        if calls["n"] == 1:
            mock_resp.json.return_value = [{"id": n, "valid_start": "2023-01-01 00:00:00"} for n in range(30)]
        else:
            mock_resp.json.return_value = [{"id": 99, "valid_start": "2023-01-02 00:00:00"}]
        return mock_resp

    monkeypatch.setattr(adapter.session, "get", fake_get)
    jobs = adapter.fetch({"ats_slug": "acme"})
    assert len(jobs) == 31
    assert calls["n"] == 2


def test_traffit_fetch_missing_slug():
    adapter = TraffitAdapter()
    assert adapter.fetch({"ats_slug": ""}) == []
    assert adapter.fetch({}) == []


def test_traffit_probe_jobs(monkeypatch):
    adapter = TraffitAdapter()
    monkeypatch.setattr(
        adapter,
        "fetch",
        lambda company, **kw: [
            {
                "id": 1,
                "valid_start": "2023-01-01 00:00:00",
                "advert": {"name": "Dev", "values": [], "company_name": "Acme Sp. z o.o."},
                "options": {"remote": "1"},
            }
        ],
    )
    res = adapter.probe_jobs("acme")
    assert res["jobs_total"] == 1
    assert res["remote_hits"] == 1
    assert res["recent_job_at"] == "2023-01-01 00:00:00"
    assert res["company_name"] == "Acme Sp. z o.o."


def test_traffit_probe_jobs_empty_slug():
    adapter = TraffitAdapter()
    assert adapter.probe_jobs("") == {}
    assert adapter.probe_jobs("   ") == {}


def test_traffit_probe_jobs_empty_fetch(monkeypatch):
    adapter = TraffitAdapter()
    monkeypatch.setattr(adapter, "fetch", lambda company, **kw: [])
    assert adapter.probe_jobs("acme") == {}


def test_traffit_normalize_success():
    adapter = TraffitAdapter()
    raw_job = {
        "_ats_slug": "acme-hr",
        "id": 42,
        "url": "https://acme-hr.traffit.com/public/an/xx",
        "advert": {
            "name": "Backend Dev",
            "values": [
                {"field_id": "description", "value": "<p>Hello</p>"},
                {"field_id": "requirements", "value": "<p>Reqs</p>"},
            ],
        },
        "options": {
            "job_location": '{"locality": "Warsaw", "country": "Poland"}',
            "branches": "IT",
        },
    }
    job = adapter.normalize(raw_job)
    assert job is not None
    assert job["job_id"] == "traffit:acme-hr:42"
    assert job["source"] == "traffit:acme-hr"
    assert job["company_name"] == "Acme Hr"
    assert job["department"] == "IT"
    assert "Hello" in job["description"]
    assert "Reqs" in job["description"]


def test_traffit_normalize_missing_slug_and_id():
    adapter = TraffitAdapter()
    assert adapter.normalize({"id": 1, "advert": {"name": "X"}}) is None
    assert adapter.normalize({"_ats_slug": "x", "advert": {}}) is None
