import pytest
import requests
from unittest.mock import MagicMock
from app.workers.ingestion.fetch import FetchCompanyJobsError, fetch_company_jobs


def test_fetch_company_jobs_success():
    adapter = MagicMock()
    adapter.fetch.return_value = [{"id": 1}, {"id": 2}]
    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}

    jobs, err = fetch_company_jobs(company, adapter)
    assert err is None
    assert list(jobs) == [{"id": 1}, {"id": 2}]


def test_fetch_company_jobs_wraps_mid_stream_network_error():
    def _stream():
        yield {"id": 1}
        raise requests.ConnectionError("Connection dropped")

    adapter = MagicMock()
    adapter.fetch.return_value = _stream()
    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}

    jobs, err = fetch_company_jobs(company, adapter)

    assert err is None
    assert next(jobs) == {"id": 1}
    with pytest.raises(FetchCompanyJobsError, match="fetch_network_failed") as exc_info:
        next(jobs)
    assert exc_info.value.error_code == "fetch_network_failed"


def test_fetch_company_jobs_http_error_404():
    adapter = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    adapter.fetch.side_effect = requests.HTTPError("404 Not Found", response=mock_resp)

    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}
    jobs, err = fetch_company_jobs(company, adapter)
    assert jobs is None
    assert err == "invalid_ats_slug"


def test_fetch_company_jobs_http_error_other():
    adapter = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    adapter.fetch.side_effect = requests.HTTPError("500 Server Error", response=mock_resp)

    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}
    jobs, err = fetch_company_jobs(company, adapter)
    assert jobs is None
    assert err == "fetch_failed"


def test_fetch_company_jobs_network_error():
    adapter = MagicMock()
    adapter.fetch.side_effect = requests.ConnectionError("Connection Refused")

    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}
    jobs, err = fetch_company_jobs(company, adapter)
    assert jobs is None
    assert err == "fetch_network_failed"


def test_fetch_company_jobs_request_exception():
    adapter = MagicMock()
    adapter.fetch.side_effect = requests.RequestException("General Request Error")

    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}
    jobs, err = fetch_company_jobs(company, adapter)
    assert jobs is None
    assert err == "fetch_failed"


def test_fetch_company_jobs_unhandled_exception():
    adapter = MagicMock()
    adapter.fetch.side_effect = ValueError("Something unexpected")

    company = {"ats_provider": "greenhouse", "company_id": "c1", "ats_slug": "acme"}
    jobs, err = fetch_company_jobs(company, adapter)
    assert jobs is None
    assert err == "fetch_failed"
