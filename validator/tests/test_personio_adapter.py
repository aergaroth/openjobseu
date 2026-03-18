import pytest
from unittest.mock import MagicMock

from app.adapters.ats.personio import PersonioAdapter

def test_personio_fetch_parses_xml(monkeypatch):
    xml_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
    <workzag-jobs>
        <position>
            <id>123</id>
            <name>Backend Engineer</name>
            <jobDescriptions>
                <jobDescription>
                    <name>Requirements</name>
                    <value><![CDATA[Python, SQL]]></value>
                </jobDescription>
            </jobDescriptions>
            <office>Remote</office>
            <department>Engineering</department>
            <createdAt>2023-01-01T12:00:00Z</createdAt>
        </position>
    </workzag-jobs>
    """
    
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [xml_payload]
    mock_resp.raise_for_status = MagicMock()
    
    adapter = PersonioAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    jobs = adapter.fetch({"ats_slug": "test-company"})
    
    assert len(jobs) == 1
    assert jobs[0]["id"] == "123"
    assert jobs[0]["name"] == "Backend Engineer"
    assert "Requirements" in jobs[0]["description"]
    assert "Python, SQL" in jobs[0]["description"]
    assert jobs[0]["office"] == "Remote"
    assert jobs[0]["department"] == "Engineering"
    assert jobs[0]["_ats_slug"] == "test-company"

def test_personio_fetch_missing_slug():
    adapter = PersonioAdapter()
    jobs = adapter.fetch({"ats_slug": ""})
    assert jobs == []

def test_personio_fetch_exceeds_size_limit(monkeypatch):
    mock_resp = MagicMock()
    # chunk size > 10MB to trigger safety mechanism
    mock_resp.iter_content.return_value = [b"A" * (11 * 1024 * 1024)]
    mock_resp.raise_for_status = MagicMock()
    
    adapter = PersonioAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    with pytest.raises(ValueError, match="too large"):
        adapter.fetch({"ats_slug": "test-company"})

def test_personio_fetch_invalid_xml(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"<not-closed>"]
    mock_resp.raise_for_status = MagicMock()
    
    adapter = PersonioAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda *a, **kw: mock_resp)
    
    with pytest.raises(ValueError, match="XML parse failed"):
        adapter.fetch({"ats_slug": "test-company"})

def test_personio_normalize_deduces_remote_flag_correctly():
    adapter = PersonioAdapter()
    
    assert adapter.normalize({"id": "1", "_ats_slug": "a", "name": "Remote Engineer", "office": "Berlin"})["remote_source_flag"] is True
    assert adapter.normalize({"id": "2", "_ats_slug": "a", "name": "Engineer", "office": "EU Remote"})["remote_source_flag"] is True
    assert adapter.normalize({"id": "3", "_ats_slug": "a", "name": "Engineer", "office": "Berlin"})["remote_source_flag"] is False