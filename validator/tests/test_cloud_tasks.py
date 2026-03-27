import requests
from unittest.mock import MagicMock, patch

import pytest

from app.utils.cloud_tasks import CLOUD_PLATFORM_SCOPE, create_tick_task, is_tick_queue_configured


def _set_queue_env(monkeypatch):
    monkeypatch.setenv("TICK_TASK_QUEUE_PROJECT", "test-project")
    monkeypatch.setenv("TICK_TASK_QUEUE_LOCATION", "test-location")
    monkeypatch.setenv("TICK_TASK_QUEUE_NAME", "test-queue")


def test_is_tick_queue_configured(monkeypatch):
    """Test sprawdzenia konfiguracji kolejki Cloud Tasks."""
    _set_queue_env(monkeypatch)
    assert is_tick_queue_configured() is True

    monkeypatch.delenv("TICK_TASK_QUEUE_PROJECT")
    assert is_tick_queue_configured() is False

    monkeypatch.delenv("TICK_TASK_QUEUE_LOCATION")
    monkeypatch.delenv("TICK_TASK_QUEUE_NAME")
    assert is_tick_queue_configured() is False


def test_create_tick_task_success(monkeypatch):
    """Test tworzenia zadania Cloud Tasks z poprawnymi parametrami."""
    _set_queue_env(monkeypatch)
    mock_payload = {"incremental": True}
    mock_headers = {"Content-Type": "application/json"}
    mock_credentials = object()

    with (
        patch(
            "app.utils.cloud_tasks.google.auth.default", return_value=(mock_credentials, "test-project")
        ) as mock_auth,
        patch("app.utils.cloud_tasks.AuthorizedSession") as mock_session_cls,
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/test-location/queues/test-queue/tasks/tick-test-task"
        }
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value = mock_response

        result = create_tick_task(
            task_id="test-task",
            handler_url="https://example.com/handler",
            payload=mock_payload,
            headers=mock_headers,
        )

        assert result["name"].endswith("/tasks/tick-test-task")
        mock_auth.assert_called_once_with(scopes=[CLOUD_PLATFORM_SCOPE])
        mock_session_cls.assert_called_once_with(mock_credentials)
        mock_session.post.assert_called_once()
        _, kwargs = mock_session.post.call_args
        assert kwargs["json"]["task"]["httpRequest"]["url"] == "https://example.com/handler"
        assert kwargs["json"]["task"]["httpRequest"]["headers"] == mock_headers
        mock_response.raise_for_status.assert_called_once()


def test_create_tick_task_missing_environment_variables(monkeypatch):
    """Test tworzenia zadania bez zmiennych środowiskowych."""
    monkeypatch.delenv("TICK_TASK_QUEUE_PROJECT", raising=False)
    monkeypatch.delenv("TICK_TASK_QUEUE_LOCATION", raising=False)
    monkeypatch.delenv("TICK_TASK_QUEUE_NAME", raising=False)

    with pytest.raises(KeyError):
        create_tick_task(
            task_id="test-task",
            handler_url="https://example.com/handler",
            payload={},
            headers={},
        )


def test_create_tick_task_api_error(monkeypatch):
    """Test obsługi błędu API Cloud Tasks."""
    _set_queue_env(monkeypatch)
    http_error = requests.exceptions.HTTPError(response=MagicMock(text="API Error"))

    with (
        patch("app.utils.cloud_tasks.google.auth.default", return_value=(object(), "test-project")),
        patch("app.utils.cloud_tasks.AuthorizedSession") as mock_session_cls,
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = http_error
        mock_session_cls.return_value.post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            create_tick_task(
                task_id="test-task",
                handler_url="https://example.com/handler",
                payload={},
                headers={},
            )


def test_create_tick_task_invalid_headers(monkeypatch):
    """Test usuwania pustych i konfliktowych nagłówków."""
    _set_queue_env(monkeypatch)
    mock_headers = {
        "Authorization": "Bearer token",
        "authorization": "lowercase token",
        "Content-Type": "application/json",
        "X-Test-Header": "",
    }

    with (
        patch("app.utils.cloud_tasks.google.auth.default", return_value=(object(), "test-project")),
        patch("app.utils.cloud_tasks.AuthorizedSession") as mock_session_cls,
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "task-name"}
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value = mock_response

        create_tick_task(
            task_id="test-task",
            handler_url="https://example.com/handler",
            payload={},
            headers=mock_headers,
        )

        _, kwargs = mock_session.post.call_args
        sent_headers = kwargs["json"]["task"]["httpRequest"]["headers"]
        assert "Authorization" not in sent_headers
        assert "authorization" not in sent_headers
        assert "X-Test-Header" not in sent_headers
        assert sent_headers["Content-Type"] == "application/json"


def test_create_tick_task_oidc_token(monkeypatch):
    """Test dodawania tokenu OIDC do żądania."""
    _set_queue_env(monkeypatch)
    monkeypatch.setenv("SCHEDULER_SA_EMAIL", "test-sa@example.com")
    monkeypatch.setenv("BASE_URL", "https://example.com")

    with (
        patch("app.utils.cloud_tasks.google.auth.default", return_value=(object(), "test-project")),
        patch("app.utils.cloud_tasks.AuthorizedSession") as mock_session_cls,
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "task-name"}
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value = mock_response

        create_tick_task(
            task_id="test-task",
            handler_url="https://example.com/handler",
            payload={"incremental": True},
            headers={},
        )

        _, kwargs = mock_session.post.call_args
        sent_request = kwargs["json"]["task"]["httpRequest"]
        assert sent_request["oidcToken"]["serviceAccountEmail"] == "test-sa@example.com"
        assert sent_request["oidcToken"]["audience"] == "https://example.com"


def test_create_tick_task_empty_payload(monkeypatch):
    """Test tworzenia zadania z pustym payloadem."""
    _set_queue_env(monkeypatch)

    with (
        patch("app.utils.cloud_tasks.google.auth.default", return_value=(object(), "test-project")),
        patch("app.utils.cloud_tasks.AuthorizedSession") as mock_session_cls,
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "projects/test-project/locations/test-location/queues/test-queue/tasks/tick-test-task"
        }
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value = mock_response

        result = create_tick_task(
            task_id="test-task",
            handler_url="https://example.com/handler",
            payload={},
            headers={},
        )

        assert result["name"].endswith("/tasks/tick-test-task")
        _, kwargs = mock_session.post.call_args
        assert kwargs["json"]["task"]["httpRequest"]["body"] == "e30="
