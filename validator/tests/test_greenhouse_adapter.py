import pytest
from unittest.mock import MagicMock
from app.adapters.ats.greenhouse import GreenhouseAdapter


def test_greenhouse_normalize_deduces_remote_flag_correctly():
    adapter = GreenhouseAdapter()

    # 1. Pole location przekazane jako czysty ciąg znaków "Remote"
    assert adapter.normalize({
        "id": "1",
        "_ats_board_token": "acme",
        "title": "Engineer",
        "location": "Remote",
        "absolute_url": "https://example.com/1"
    })["remote_source_flag"] is True

    # 2. Pole location przekazane jako obiekt słownikowy (częsty przypadek w Greenhouse API)
    assert adapter.normalize({
        "id": "2",
        "_ats_board_token": "acme",
        "title": "Engineer",
        "location": {"name": "EU Remote"},
        "absolute_url": "https://example.com/2"
    })["remote_source_flag"] is True

    # 3. Zwykła lokalizacja biurowa (dla weryfikacji braku "fałszywych alarmów")
    assert adapter.normalize({
        "id": "3",
        "_ats_board_token": "acme",
        "title": "Engineer",
        "location": "Berlin",
        "absolute_url": "https://example.com/3"
    })["remote_source_flag"] is False


def test_greenhouse_extract_jobs_payload_types():
    adapter = GreenhouseAdapter()
    
    # Weryfikacja obu formatów, z jakich rzuca API Greenhouse (dict albo lista)
    assert adapter._extract_jobs_from_payload([{"id": 1}], "test") == [{"id": 1}]
    assert adapter._extract_jobs_from_payload({"jobs": [{"id": 2}]}, "test") == [{"id": 2}]
    
    with pytest.raises(ValueError, match="does not contain a jobs list"):
        adapter._extract_jobs_from_payload({"jobs": "not a list"}, "test")
        
    with pytest.raises(ValueError, match="did not return a list or dict"):
        adapter._extract_jobs_from_payload("string format", "test")


def test_greenhouse_probe_jobs_success(monkeypatch):
    adapter = GreenhouseAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobs": [
        {"title": "Dev", "location": {"name": "Remote"}, "updated_at": "2023-01-01"},
        {"title": "Dev 2", "location": "Remote"},
        "not a dict"
    ]}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    res = adapter.probe_jobs("test")
    assert res["jobs_total"] == 2
    assert res["remote_hits"] == 2
    assert res["recent_job_at"] is not None

def test_greenhouse_probe_jobs_empty_slug():
    with pytest.raises(ValueError):
        GreenhouseAdapter().probe_jobs("")
        
def test_greenhouse_fetch_missing_slug():
    with pytest.raises(ValueError):
        GreenhouseAdapter().fetch({"ats_slug": ""})
        
def test_greenhouse_fallback_company_name():
    assert GreenhouseAdapter._fallback_company_name("acme-inc") == "acme inc"


def test_greenhouse_fetch_success(monkeypatch):
    adapter = GreenhouseAdapter()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"jobs": [{"id": 1, "title": "Dev", "updated_at": "2023-01-01T00:00:00Z"}]}
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    jobs = adapter.fetch({"ats_slug": "test-slug"})
    assert len(jobs) == 1
    assert jobs[0]["_ats_board_token"] == "test-slug"

def test_greenhouse_normalize_missing_token():
    adapter = GreenhouseAdapter()
    with pytest.raises(ValueError, match="Missing _ats_board_token"):
        adapter.normalize({"id": 1, "title": "Dev"})

def test_greenhouse_normalize_incomplete_job():
    adapter = GreenhouseAdapter()
    # Brak absolute_url
    assert adapter.normalize({"_ats_board_token": "acme", "id": 1, "title": "Dev"}) is None
    # Brak id
    assert adapter.normalize({"_ats_board_token": "acme", "title": "Dev", "absolute_url": "url"}) is None

def test_greenhouse_normalize_complex_fields():
    adapter = GreenhouseAdapter()
    job = adapter.normalize({
        "_ats_board_token": "acme",
        "id": "123",
        "title": "Engineer",
        "absolute_url": "https://example.com/123",
        "location": "Berlin",
        "departments": [{"name": 123}], # Test rzutowania int->str dla nazwy departamentu
        "pay_bounds": [{"min_value": 50000, "max_value": 70000}],
        "pubDate": "2023-01-01T12:00:00Z"
    })
    assert job["department"] == "123"
    assert job["salary_min"] == 50000
    assert job["salary_max"] == 70000
    assert "2023-01-01" in job["first_seen_at"]

def test_greenhouse_probe_jobs_pubdate_fallback(monkeypatch):
    adapter = GreenhouseAdapter()
    mock_resp = MagicMock()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    # Mockujemy sytuację, w której brakuje updated_at, lecz dostępne jest pole pubDate
    monkeypatch.setattr(adapter, "_parse_json", lambda *a, **kw: [{"title": "Dev", "pubDate": "2023-01-01T00:00:00Z"}])
    res = adapter.probe_jobs("test")
    assert res["recent_job_at"] is not None
    assert res["recent_job_at"].year == 2023