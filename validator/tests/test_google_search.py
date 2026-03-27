from unittest.mock import MagicMock, patch

import requests

from app.utils.google_search import google_custom_search


def _set_google_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")


def test_google_search_success(monkeypatch):
    """Test udanego wyszukiwania z zamockowanym API Google."""
    _set_google_env(monkeypatch)
    mock_response = {
        "items": [
            {"link": "https://example.com/job1"},
            {"link": "https://example.com/job2"},
            {"link": "https://example.com/job3"},
        ]
    }

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response

        result = google_custom_search("test query", num_results=3, start=1)

        assert result == ["https://example.com/job1", "https://example.com/job2", "https://example.com/job3"]
        mock_get.assert_called_once()
        mock_get.return_value.raise_for_status.assert_called_once()


def test_google_search_no_results(monkeypatch):
    """Test odpowiedzi bez wyników."""
    _set_google_env(monkeypatch)

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {}

        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_called_once()


def test_google_search_api_error(monkeypatch):
    """Test obsługi nieoczekiwanego błędu po stronie klienta."""
    _set_google_env(monkeypatch)

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.side_effect = Exception("API Error")

        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_called_once()


def test_google_search_request_exception(monkeypatch):
    """Test obsługi wyjątku requests.RequestException."""
    _set_google_env(monkeypatch)

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Request Exception")

        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_called_once()


def test_google_search_missing_api_key(monkeypatch):
    """Test braku klucza API."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

    with patch("app.utils.google_search.requests.get") as mock_get:
        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_not_called()


def test_google_search_missing_cx_id(monkeypatch):
    """Test braku ID wyszukiwarki."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.delenv("GOOGLE_CSE_ID", raising=False)

    with patch("app.utils.google_search.requests.get") as mock_get:
        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_not_called()


def test_google_search_http_error(monkeypatch):
    """Test obsługi błędu HTTP."""
    _set_google_env(monkeypatch)

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP Error")
        mock_get.return_value = mock_response

        result = google_custom_search("test query")

        assert result == []
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()


def test_google_search_custom_parameters(monkeypatch):
    """Test z niestandardowymi parametrami."""
    _set_google_env(monkeypatch)
    mock_response = {"items": [{"link": "https://example.com/job1"}]}

    with patch("app.utils.google_search.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response

        result = google_custom_search("test query", num_results=5, start=11)

        assert result == ["https://example.com/job1"]
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["num"] == 5
        assert kwargs["params"]["start"] == 11
