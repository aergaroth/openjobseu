from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.workers.ingestion.employer as employer_worker

client = TestClient(app)

def test_tick_endpoint_incremental_false(monkeypatch):
    """
    Verifies if calling the endpoint with incremental=false
    effectively modifies the GLOBAL_INCREMENTAL_FETCH flag in the employer module.
    """
    # Ensure the flag is set to True before the test
    monkeypatch.setattr(employer_worker, "GLOBAL_INCREMENTAL_FETCH", True)
    
    # Mock run_pipeline to avoid running the actual process in the endpoint test
    with patch("app.api.system.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {"status": "ok", "actions": []}
        
        # TestClient bypasses internal security by default (see: test_auth.py)
        response = client.post("/internal/tick?incremental=false")
        
        assert response.status_code == 200
        # After calling the endpoint, the flag should be set to False
        assert employer_worker.GLOBAL_INCREMENTAL_FETCH is False

def test_tick_endpoint_limit_parameter(monkeypatch):
    """
    Verifies if calling the endpoint with a custom limit parameter
    effectively modifies the GLOBAL_COMPANIES_LIMIT flag.
    """
    # Ensure the default limit is set
    monkeypatch.setattr(employer_worker, "GLOBAL_COMPANIES_LIMIT", 100)
    
    with patch("app.api.system.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {"status": "ok", "actions": []}
        
        # Call with a custom limit
        response = client.post("/internal/tick?limit=42")
        
        assert response.status_code == 200
        assert employer_worker.GLOBAL_COMPANIES_LIMIT == 42

def test_ingest_company_respects_incremental_flag_false(monkeypatch):
    """
    Verifies if, with the flag set to False, the ingest_company function
    hides the last sync date from the adapter (passes None).
    """
    monkeypatch.setattr(employer_worker, "GLOBAL_INCREMENTAL_FETCH", False)
    
    mock_adapter = MagicMock()
    mock_adapter.active = True
    mock_adapter.fetch.return_value = []
    
    company = {
        "company_id": "test-123",
        "ats_provider": "workable",
        "ats_slug": "test-slug",
        "last_sync_at": "2023-01-01T00:00:00Z"
    }
    
    with patch("app.workers.ingestion.employer.get_adapter", return_value=mock_adapter), \
         patch("app.workers.ingestion.employer.get_engine"):
         
        employer_worker.ingest_company(company)
        
        # Expect updated_since=None to be passed (ignoring '2023-01-01T00:00:00Z')
        mock_adapter.fetch.assert_called_once_with(company, updated_since=None)

def test_ingest_company_uses_last_sync_at_when_incremental_true(monkeypatch):
    """
    Verifies the default state where the flag is True and the date is passed normally.
    """
    monkeypatch.setattr(employer_worker, "GLOBAL_INCREMENTAL_FETCH", True)
    mock_adapter = MagicMock()
    company = {"ats_provider": "workable", "last_sync_at": "2023-05-05T00:00:00Z"}
    
    with patch("app.workers.ingestion.employer.get_adapter", return_value=mock_adapter), \
         patch("app.workers.ingestion.employer.get_engine"):
        employer_worker.ingest_company(company)
        mock_adapter.fetch.assert_called_once_with(company, updated_since="2023-05-05T00:00:00Z")

def test_run_employer_ingestion_respects_global_companies_limit(monkeypatch):
    """
    Verifies if the employer ingestion worker passes the global limit flag
    to the database load function.
    """
    monkeypatch.setattr(employer_worker, "GLOBAL_COMPANIES_LIMIT", 15)
    
    mock_load = MagicMock(return_value=[])
    monkeypatch.setattr(employer_worker, "load_active_ats_companies", mock_load)
    
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    monkeypatch.setattr(employer_worker, "get_engine", lambda: mock_engine)
    
    employer_worker.run_employer_ingestion()
    
    mock_load.assert_called_once_with(mock_conn, limit=15)