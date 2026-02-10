import json
import logging

from app import logging as app_logging


def test_should_use_text_logs_when_app_runtime_local(monkeypatch):
    monkeypatch.setenv("APP_RUNTIME", "local")
    monkeypatch.setenv("K_SERVICE", "set-but-ignored")

    assert app_logging.should_use_text_logs() is True


def test_should_use_json_logs_when_app_runtime_not_local(monkeypatch):
    monkeypatch.setenv("APP_RUNTIME", "cloud")

    assert app_logging.should_use_text_logs() is False


def test_should_use_text_logs_in_fallback_when_not_in_container(monkeypatch):
    monkeypatch.delenv("APP_RUNTIME", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("ECS_CONTAINER_METADATA_URI", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setattr(app_logging.os.path, "exists", lambda _: False)

    assert app_logging.should_use_text_logs() is True


def test_should_use_json_logs_in_fallback_when_in_container(monkeypatch):
    monkeypatch.delenv("APP_RUNTIME", raising=False)
    monkeypatch.setenv("K_SERVICE", "openjobseu-runtime")

    assert app_logging.should_use_text_logs() is False


def test_configure_logging_uses_text_formatter_for_local(monkeypatch):
    monkeypatch.setenv("APP_RUNTIME", "local")

    app_logging.configure_logging()

    root = logging.getLogger()
    assert isinstance(root.handlers[0].formatter, app_logging.SafeExtraFormatter)


def test_configure_logging_uses_json_formatter_for_cloud(monkeypatch):
    monkeypatch.setenv("APP_RUNTIME", "cloud")

    app_logging.configure_logging()

    root = logging.getLogger()
    assert isinstance(root.handlers[0].formatter, app_logging.JsonLogFormatter)


def test_json_formatter_renders_json_with_extras():
    formatter = app_logging.JsonLogFormatter()
    record = logging.makeLogRecord(
        {
            "name": "openjobseu.test",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "tick complete",
            "args": (),
            "ingested": 5,
            "source": "remotive",
        }
    )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "openjobseu.test"
    assert payload["message"] == "tick complete"
    assert payload["ingested"] == 5
    assert payload["source"] == "remotive"
