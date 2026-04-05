import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import pytest_precommit_guard as guard


def test_resolve_test_database_url_defaults_to_local_testdb():
    assert guard.resolve_test_database_url({}) == guard.DEFAULT_TEST_URL


def test_should_skip_when_safe_test_db_is_unavailable(monkeypatch):
    monkeypatch.setattr(guard, "database_is_available", lambda url: False)

    should_skip, message = guard.should_skip_pytest_hook(
        {"DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"}
    )

    assert should_skip is True
    assert "should be skipped" in message


def test_should_not_skip_when_safe_test_db_is_available(monkeypatch):
    monkeypatch.setattr(guard, "database_is_available", lambda url: True)

    should_skip, message = guard.should_skip_pytest_hook(
        {"DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"}
    )

    assert should_skip is False
    assert message == "Test database is available."


def test_should_not_skip_unsafe_database_url(monkeypatch):
    called = False

    def fake_database_is_available(url: str) -> bool:
        nonlocal called
        called = True
        return False

    monkeypatch.setattr(guard, "database_is_available", fake_database_is_available)

    should_skip, message = guard.should_skip_pytest_hook(
        {"DATABASE_URL": "postgresql+psycopg://prod-dbuser:secret@db.example.com:25060/openjobseu?sslmode=require"}
    )

    assert should_skip is False
    assert "running pytest hook normally" in message
    assert called is False
