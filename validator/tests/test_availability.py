import pytest
from concurrent.futures import TimeoutError
from unittest.mock import MagicMock

from app.workers.availability import _check_availability_for_jobs
import app.workers.availability as availability_module


def test_check_availability_for_jobs_happy_path(monkeypatch):
    jobs = [{"job_id": "1"}, {"job_id": "2"}, {"job_id": "3"}]
    
    def mock_check(job, **kwargs):
        mapping = {"1": "active", "2": "expired", "3": "unreachable"}
        return mapping[job["job_id"]]
        
    monkeypatch.setattr(availability_module, "check_job_availability", mock_check)
    
    statuses = _check_availability_for_jobs(jobs)
    assert statuses == ["active", "expired", "unreachable"]


def test_check_availability_for_jobs_timeout(monkeypatch):
    jobs = [{"job_id": "1"}, {"job_id": "2"}]
    
    # Mockujemy as_completed tak, aby od razu wyrzucało TimeoutError
    def mock_as_completed(fs, timeout):
        raise TimeoutError("Simulated timeout")
        
    monkeypatch.setattr(availability_module, "as_completed", mock_as_completed)
    
    log_calls = []
    monkeypatch.setattr(availability_module.logger, "error", lambda msg, extra=None: log_calls.append((msg, extra)))
    
    statuses = _check_availability_for_jobs(jobs)
    
    # Domyślnym statusem dla nieprzetworzonych na skutek timeoutu zapytań jest "unreachable"
    assert statuses == ["unreachable", "unreachable"]
    
    # Upewniamy się, że TimeoutError został poprawnie obsłużony i zalogowany (bez wywalania workera)
    assert len(log_calls) == 1
    assert log_calls[0][0] == "availability_pool_timeout"
    assert log_calls[0][1]["msg"] == "Thread pool exhausted on hanging requests"


def test_check_availability_for_jobs_future_exception(monkeypatch):
    jobs = [{"job_id": "1"}, {"job_id": "2"}]
    
    def mock_check(job, **kwargs):
        if job["job_id"] == "1":
            raise ValueError("Simulated unexpected thread failure")
        return "active"
        
    monkeypatch.setattr(availability_module, "check_job_availability", mock_check)
    
    statuses = _check_availability_for_jobs(jobs)
    
    # Oferta która rzuciła wyjątkiem powinna pozostać nieosiągalna (unreachable), a pętla powinna przetworzyć resztę
    assert statuses == ["unreachable", "active"]


def test_check_availability_for_jobs_empty_and_single(monkeypatch):
    assert _check_availability_for_jobs([]) == []
    
    monkeypatch.setattr(availability_module, "check_job_availability", lambda j, **kw: "expired")
    assert _check_availability_for_jobs([{"job_id": "1"}]) == ["expired"]