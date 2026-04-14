import pytest
import requests
from unittest.mock import MagicMock
from app.adapters.ats.teamtailor import TeamtailorAdapter

# ---------------------------------------------------------------------------
# Test fixtures / factories
# ---------------------------------------------------------------------------

INCLUDED_DEPT = {
    "id": "99",
    "type": "departments",
    "attributes": {"name": "Engineering"},
}
INCLUDED_LOC = {
    "id": "77",
    "type": "locations",
    "attributes": {"city": "Amsterdam", "country": "Netherlands", "remote-enabled": True},
}
INCLUDED_LOC_2 = {
    "id": "88",
    "type": "locations",
    "attributes": {"city": "Berlin", "country": "Germany"},
}


def _make_job(
    job_id="12345",
    title="Backend Engineer",
    remote_status="none",
    dept_id="99",
    loc_ids=None,
    with_salary=True,
    company_name=None,
):
    loc_ids = loc_ids or ["77"]
    attrs = {
        "title": title,
        "body": "<p>HTML description</p>",
        "remote-status": remote_status,
        "status": "open",
        "created-at": "2024-01-15T10:00:00.000Z",
        "updated-at": "2024-03-01T12:00:00.000Z",
    }
    if with_salary:
        attrs.update(
            {
                "salary-min": 60000,
                "salary-max": 90000,
                "salary-currency": "EUR",
                "salary-time-unit": "yearly",
            }
        )
    if company_name:
        attrs["company-name"] = company_name
    return {
        "id": job_id,
        "type": "jobs",
        "links": {"careersite-job-url": f"https://jobs.company.com/jobs/{job_id}-title"},
        "attributes": attrs,
        "relationships": {
            "department": {"data": {"id": dept_id, "type": "departments"}},
            "locations": {"data": [{"id": lid, "type": "locations"} for lid in loc_ids]},
        },
    }


def _make_response(jobs_data, included_data=None, total_pages=1, record_count=None):
    if record_count is None:
        record_count = len(jobs_data)
    return {
        "data": jobs_data,
        "included": included_data or [],
        "meta": {
            "record-count": record_count,
            "page-count": total_pages,
            "total-pages": total_pages,
        },
    }


def _mock_resp(payload):
    m = MagicMock()
    m.json.return_value = payload
    return m


def _raw_job_with_injected(job, token="token123", included_data=None):
    """Simulate what fetch() injects into a raw job before normalize() sees it."""
    if included_data is None:
        included_data = [INCLUDED_DEPT, INCLUDED_LOC]
    from app.adapters.ats.teamtailor import TeamtailorAdapter as _T

    included = _T._build_included_lookups(included_data)
    job = dict(job)
    job["_ats_slug"] = token
    job["_included"] = included
    job["_updated_at_flat"] = (job.get("attributes") or {}).get("updated-at")
    return job


# ---------------------------------------------------------------------------
# fetch() tests
# ---------------------------------------------------------------------------


def test_teamtailor_dorking_target_is_none():
    """Teamtailor uses per-company API tokens — dorking would yield unusable subdomains."""
    assert TeamtailorAdapter.dorking_target is None


def test_teamtailor_fetch_raises_on_http_error(monkeypatch):
    """A 401/403 from the API must propagate as HTTPError, not return empty jobs silently."""
    adapter = TeamtailorAdapter()

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError(response=MagicMock(status_code=401))
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(requests.HTTPError):
        adapter.fetch({"ats_slug": "bad-token"})


def test_teamtailor_probe_raises_on_http_error(monkeypatch):
    """A 401 during probe must propagate so ats_probe.py can return None cleanly."""
    adapter = TeamtailorAdapter()

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError(response=MagicMock(status_code=401))
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(requests.HTTPError):
        adapter.probe_jobs("bad-token")


def test_teamtailor_fetch_missing_token():
    adapter = TeamtailorAdapter()
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.fetch({"ats_slug": ""})


def test_teamtailor_fetch_missing_slug_key():
    adapter = TeamtailorAdapter()
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.fetch({})


def test_teamtailor_fetch_invalid_payload(monkeypatch):
    adapter = TeamtailorAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda *a, **kw: _mock_resp({"data": "not-a-list", "meta": {}}),
    )
    with pytest.raises(ValueError, match="did not return a data list"):
        adapter.fetch({"ats_slug": "token123"})


def test_teamtailor_fetch_single_page(monkeypatch):
    adapter = TeamtailorAdapter()
    payload = _make_response([_make_job()], [INCLUDED_DEPT, INCLUDED_LOC])
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: _mock_resp(payload))

    jobs = adapter.fetch({"ats_slug": "token123"})

    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "token123"
    assert ("departments", "99") in jobs[0]["_included"]
    assert ("locations", "77") in jobs[0]["_included"]
    assert jobs[0]["_updated_at_flat"] == "2024-03-01T12:00:00.000Z"


def test_teamtailor_fetch_multi_page(monkeypatch):
    adapter = TeamtailorAdapter()

    def mock_get(url, params=None, headers=None, **kwargs):
        page_num = (params or {}).get("page[number]", 1)
        if page_num == 1:
            return _mock_resp(
                _make_response([_make_job("1")], [INCLUDED_DEPT, INCLUDED_LOC], total_pages=2, record_count=2)
            )
        return _mock_resp(
            _make_response([_make_job("2")], [INCLUDED_DEPT, INCLUDED_LOC], total_pages=2, record_count=2)
        )

    monkeypatch.setattr(adapter.session, "get", mock_get)

    jobs = adapter.fetch({"ats_slug": "token123"})

    assert len(jobs) == 2
    assert {j["id"] for j in jobs} == {"1", "2"}


def test_teamtailor_fetch_sends_auth_header(monkeypatch):
    adapter = TeamtailorAdapter()
    captured_headers = {}

    def mock_get(url, params=None, headers=None, **kwargs):
        captured_headers.update(headers or {})
        return _mock_resp(_make_response([]))

    monkeypatch.setattr(adapter.session, "get", mock_get)
    adapter.fetch({"ats_slug": "mytoken"})

    assert captured_headers.get("Authorization") == "Token token=mytoken"
    assert captured_headers.get("X-Api-Version") == "20161108"


# ---------------------------------------------------------------------------
# probe_jobs() tests
# ---------------------------------------------------------------------------


def test_teamtailor_probe_empty_slug():
    adapter = TeamtailorAdapter()
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.probe_jobs("")


def test_teamtailor_probe_invalid_payload(monkeypatch):
    adapter = TeamtailorAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda *a, **kw: _mock_resp({"data": 42, "meta": {}}),
    )
    with pytest.raises(ValueError, match="did not return a data list"):
        adapter.probe_jobs("token123")


def test_teamtailor_probe_success(monkeypatch):
    adapter = TeamtailorAdapter()
    payload = _make_response(
        [
            _make_job("1", remote_status="full", company_name="Teamtailor Example AB"),
            _make_job("2", remote_status="none"),
        ],
        [INCLUDED_DEPT, INCLUDED_LOC],
        record_count=5,
    )
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: _mock_resp(payload))

    result = adapter.probe_jobs("token123")

    assert result["jobs_total"] == 5
    assert result["remote_hits"] == 1
    assert result["recent_job_at"] is not None
    assert result["company_name"] == "Teamtailor Example AB"


def test_teamtailor_probe_empty_result(monkeypatch):
    adapter = TeamtailorAdapter()
    payload = _make_response([], record_count=0)
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: _mock_resp(payload))

    result = adapter.probe_jobs("token123")

    assert result["jobs_total"] == 0
    assert result["remote_hits"] == 0
    assert result["recent_job_at"] is None


# ---------------------------------------------------------------------------
# normalize() tests
# ---------------------------------------------------------------------------


def test_teamtailor_normalize_missing_slug_raises():
    adapter = TeamtailorAdapter()
    with pytest.raises(ValueError, match="Missing _ats_slug"):
        adapter.normalize({})


def test_teamtailor_normalize_missing_id_returns_none():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job())
    job["id"] = None
    assert adapter.normalize(job) is None


def test_teamtailor_normalize_missing_title_returns_none():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(title=""))
    assert adapter.normalize(job) is None


def test_teamtailor_normalize_missing_url_returns_none():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job())
    job["links"] = {}
    assert adapter.normalize(job) is None


def test_teamtailor_normalize_valid_job():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job())

    result = adapter.normalize(job)

    assert result is not None
    assert result["job_id"] == "teamtailor:token123:12345"
    assert result["source"] == "teamtailor:token123"
    assert result["source_job_id"] == "12345"
    assert result["title"] == "Backend Engineer"
    assert result["department"] == "Engineering"
    assert result["remote_source_flag"] is False
    assert "HTML description" in result["description"]
    assert "2024-01-15" in result["first_seen_at"]
    assert result["status"] == "new"
    assert "amsterdam" in result["remote_scope"].lower()


def test_teamtailor_normalize_remote_full():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(remote_status="full"))

    result = adapter.normalize(job)

    assert result is not None
    assert result["remote_source_flag"] is True
    assert "remote" in result["remote_scope"].lower()


def test_teamtailor_normalize_remote_hybrid():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(remote_status="hybrid"))

    result = adapter.normalize(job)

    assert result is not None
    assert result["remote_source_flag"] is False
    assert "remote" not in result["remote_scope"]


def test_teamtailor_normalize_salary():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(with_salary=True))

    result = adapter.normalize(job)

    assert result is not None
    assert result["salary_min"] == 60000
    assert result["salary_max"] == 90000
    assert result["salary_currency"] == "EUR"
    assert result["salary_period"] == "yearly"
    assert result["salary_source"] == "ats_api"


def test_teamtailor_normalize_no_salary():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(with_salary=False))

    result = adapter.normalize(job)

    assert result is not None
    assert result["salary_min"] is None
    assert result["salary_max"] is None
    assert result["salary_source"] is None


def test_teamtailor_normalize_missing_department():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(dept_id="999"), included_data=[INCLUDED_LOC])

    result = adapter.normalize(job)

    assert result is not None
    assert result["department"] is None


def test_teamtailor_normalize_multiple_locations():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(
        _make_job(loc_ids=["77", "88"]),
        included_data=[INCLUDED_DEPT, INCLUDED_LOC, INCLUDED_LOC_2],
    )

    result = adapter.normalize(job)

    assert result is not None
    scope = result["remote_scope"]
    assert "amsterdam" in scope.lower()
    assert "berlin" in scope.lower()


def test_teamtailor_normalize_company_name_derived_from_slug():
    adapter = TeamtailorAdapter()
    job = _raw_job_with_injected(_make_job(), token="my-company-token")

    result = adapter.normalize(job)

    assert result is not None
    assert result["company_name"] == "My Company Token"
