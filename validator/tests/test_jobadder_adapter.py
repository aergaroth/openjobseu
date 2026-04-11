import pytest
from unittest.mock import MagicMock
from app.adapters.ats.jobadder import JobAdderAdapter


# ---------------------------------------------------------------------------
# fetch()
# ---------------------------------------------------------------------------


def test_jobadder_fetch_missing_slug():
    with pytest.raises(ValueError, match="cannot be empty"):
        JobAdderAdapter().fetch({"ats_slug": ""})


def test_jobadder_fetch_success(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [{"adId": 1, "updatedAt": "2023-01-01T00:00:00Z"}],
        "total": 1,
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    jobs = adapter.fetch({"ats_slug": "test-board"})

    assert len(jobs) == 1
    assert jobs[0]["_ats_slug"] == "test-board"


def test_jobadder_fetch_paginates(monkeypatch):
    """Verifies that fetch() follows offset pagination until total is exhausted."""
    adapter = JobAdderAdapter()
    call_count = 0

    def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if call_count == 1:
            mock_resp.json.return_value = {
                "items": [{"adId": i, "updatedAt": "2023-01-01T00:00:00Z"} for i in range(100)],
                "total": 150,
            }
        else:
            mock_resp.json.return_value = {
                "items": [{"adId": i, "updatedAt": "2023-01-01T00:00:00Z"} for i in range(100, 150)],
                "total": 150,
            }
        return mock_resp

    monkeypatch.setattr(adapter.session, "get", mock_get)

    jobs = adapter.fetch({"ats_slug": "test-board"})

    assert call_count == 2
    assert len(jobs) == 150
    assert all(j["_ats_slug"] == "test-board" for j in jobs if isinstance(j, dict))


def test_jobadder_fetch_invalid_response(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": "not a list", "total": 0}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(ValueError, match="did not return an items list"):
        adapter.fetch({"ats_slug": "test-board"})


def test_jobadder_fetch_incremental(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {"adId": 1, "updatedAt": "2024-06-01T00:00:00Z"},
            {"adId": 2, "updatedAt": "2023-01-01T00:00:00Z"},
        ],
        "total": 2,
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    jobs = adapter.fetch({"ats_slug": "test-board"}, updated_since="2024-01-01T00:00:00Z")

    assert len(jobs) == 1
    assert jobs[0]["adId"] == 1


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


def test_jobadder_normalize_valid_full_job():
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 99,
        "title": "Backend Developer",
        "description": "<p>Great role in a great team.</p>",
        "applicationUri": "https://jobadder.com/apply/99",
        "categories": {"location": "Berlin, Germany", "locationType": "onsite"},
        "postedAt": "2024-03-01T09:00:00Z",
        "updatedAt": "2024-03-05T12:00:00Z",
        "salary": {"min": 60000, "max": 80000, "currency": "EUR", "per": "annual"},
        "department": {"name": "Engineering"},
        "advertiser": {"name": "Acme GmbH"},
    }

    result = adapter.normalize(raw_job)

    assert result is not None
    assert result["title"] == "Backend Developer"
    assert result["source"] == "jobadder:test-board"
    assert result["source_job_id"] == "99"
    assert result["job_id"] == "jobadder:test-board:99"
    assert result["company_name"] == "Acme GmbH"
    assert result["department"] == "Engineering"
    assert result["salary_min"] == 60000
    assert result["salary_max"] == 80000
    assert result["salary_currency"] == "EUR"
    assert result["salary_period"] == "yearly"
    assert result["salary_source"] == "ats_api"
    assert result["status"] == "new"
    assert result["first_seen_at"] is not None


def test_jobadder_normalize_company_name_fallback():
    """Falls back to board_id when advertiser is absent."""
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "my-company",
        "adId": 1,
        "title": "Dev",
        "applicationUri": "https://example.com/1",
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert result["company_name"] == "My Company"


def test_jobadder_normalize_url_fallback():
    """Constructs URL from adId when applicationUri is missing."""
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 42,
        "title": "Dev",
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert "42" in result["source_url"]


def test_jobadder_normalize_bullet_points():
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 1,
        "title": "Dev",
        "applicationUri": "https://example.com/1",
        "bulletPoints": ["Great culture", "Flexible hours"],
        "description": "<p>More details.</p>",
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert "<li>Great culture</li>" in result["description"]
    assert "More details" in result["description"]


def test_jobadder_normalize_department_string():
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 1,
        "title": "Dev",
        "applicationUri": "https://example.com/1",
        "department": "Product",
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert result["department"] == "Product"


def test_jobadder_normalize_remote_explicit_flag():
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 1,
        "title": "Dev",
        "applicationUri": "https://example.com/1",
        "categories": {"location": "London, UK", "locationType": "remote"},
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert result["remote_source_flag"] is True


def test_jobadder_normalize_location_text_fallback():
    """Uses locationText when categories.location is absent."""
    adapter = JobAdderAdapter()
    raw_job = {
        "_ats_slug": "test-board",
        "adId": 1,
        "title": "Dev",
        "applicationUri": "https://example.com/1",
        "locationText": "Warsaw, Poland",
    }
    result = adapter.normalize(raw_job)
    assert result is not None
    assert "warsaw" in result["remote_scope"].lower() or result["remote_scope"] == "warsaw, poland"


# --- Invalid jobs that must return None ---


def test_jobadder_normalize_missing_id():
    adapter = JobAdderAdapter()
    result = adapter.normalize(
        {
            "_ats_slug": "test-board",
            "title": "Dev",
            "applicationUri": "https://example.com",
        }
    )
    assert result is None


def test_jobadder_normalize_missing_title():
    adapter = JobAdderAdapter()
    result = adapter.normalize(
        {
            "_ats_slug": "test-board",
            "adId": 1,
            "applicationUri": "https://example.com",
        }
    )
    assert result is None


def test_jobadder_normalize_missing_url_and_id():
    adapter = JobAdderAdapter()
    result = adapter.normalize(
        {
            "_ats_slug": "test-board",
            "adId": None,
            "title": "Dev",
        }
    )
    assert result is None


def test_jobadder_normalize_missing_slug_raises():
    adapter = JobAdderAdapter()
    with pytest.raises(ValueError, match="_ats_slug"):
        adapter.normalize({"adId": 1, "title": "Dev"})


# ---------------------------------------------------------------------------
# probe_jobs()
# ---------------------------------------------------------------------------


def test_jobadder_probe_missing_slug():
    with pytest.raises(ValueError, match="cannot be empty"):
        JobAdderAdapter().probe_jobs("")


def test_jobadder_probe_success(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "total": 42,
        "items": [
            {
                "title": "Remote Python Dev",
                "categories": {"location": "Europe", "locationType": "remote"},
                "updatedAt": "2024-03-01T00:00:00Z",
            },
            {
                "title": "Onsite Engineer",
                "categories": {"location": "London, UK", "locationType": "onsite"},
                "updatedAt": "2024-02-01T00:00:00Z",
            },
            "not a dict",
        ],
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    result = adapter.probe_jobs("test-board")

    assert result["jobs_total"] == 42
    assert result["remote_hits"] == 1
    assert result["recent_job_at"] is not None


def test_jobadder_probe_total_falls_back_to_items_count(monkeypatch):
    """When API omits 'total', falls back to len(items)."""
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {"title": "Dev", "categories": {}, "updatedAt": "2024-01-01T00:00:00Z"},
            {"title": "Dev2", "categories": {}, "updatedAt": "2024-01-02T00:00:00Z"},
        ],
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    result = adapter.probe_jobs("test-board")

    assert result["jobs_total"] == 2


def test_jobadder_probe_empty(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    result = adapter.probe_jobs("test-board")

    assert result["jobs_total"] == 0
    assert result["remote_hits"] == 0
    assert result["recent_job_at"] is None


def test_jobadder_probe_invalid_payload(monkeypatch):
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": "not a list"}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    with pytest.raises(ValueError, match="did not return an items list"):
        adapter.probe_jobs("test-board")


def test_jobadder_probe_uses_posted_at_fallback(monkeypatch):
    """postedAt is used when updatedAt is absent."""
    adapter = JobAdderAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {"title": "Dev", "categories": {}, "postedAt": "2024-01-15T00:00:00Z"},
        ]
    }
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)

    result = adapter.probe_jobs("test-board")

    assert result["recent_job_at"] is not None
