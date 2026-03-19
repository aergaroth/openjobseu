import pytest
import requests
from unittest.mock import MagicMock
from app.workers.discovery.ats_probe import probe_ats
import app.workers.discovery.ats_probe as probe_module

def test_probe_ats_success(monkeypatch):
    mock_adapter = MagicMock()
    mock_adapter.probe_jobs.return_value = {"jobs_total": 5, "remote_hits": 2}
    monkeypatch.setattr(probe_module, "get_adapter", lambda p: mock_adapter)
    
    res = probe_ats("dummy", "slug")
    assert res == {"jobs_total": 5, "remote_hits": 2}

def test_probe_ats_unsupported_provider():
    assert probe_ats("unknown_provider", "slug") is None

def test_probe_ats_not_implemented(monkeypatch):
    mock_adapter = MagicMock()
    mock_adapter.probe_jobs.side_effect = NotImplementedError()
    monkeypatch.setattr(probe_module, "get_adapter", lambda p: mock_adapter)
    
    assert probe_ats("dummy", "slug") is None

def test_probe_ats_request_exception(monkeypatch):
    mock_adapter = MagicMock()
    mock_adapter.probe_jobs.side_effect = requests.RequestException("Timeout")
    monkeypatch.setattr(probe_module, "get_adapter", lambda p: mock_adapter)
    
    assert probe_ats("dummy", "slug") is None

def test_probe_ats_general_exception(monkeypatch):
    mock_adapter = MagicMock()
    mock_adapter.probe_jobs.side_effect = ValueError("Corrupted payload")
    monkeypatch.setattr(probe_module, "get_adapter", lambda p: mock_adapter)
    
    assert probe_ats("dummy", "slug") is None