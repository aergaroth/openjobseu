#!/usr/bin/env python3
import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import InterfaceError, OperationalError


DEFAULT_TEST_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
SAFE_INDICATORS = {
    "localhost",
    "127.0.0.1",
    "testdb",
    "test",
    ":5432",
}


def resolve_test_database_url(env: dict[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return source.get("DATABASE_URL", DEFAULT_TEST_URL)


def looks_like_safe_test_database(url: str) -> bool:
    return any(indicator in url for indicator in SAFE_INDICATORS)


def database_is_available(url: str) -> bool:
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
        future=True,
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, InterfaceError):
        return False
    finally:
        engine.dispose()


def should_skip_pytest_hook(env: dict[str, str] | None = None) -> tuple[bool, str]:
    url = resolve_test_database_url(env)

    # Unsafe DATABASE_URL values should still fail loudly inside pytest/conftest.
    if not looks_like_safe_test_database(url):
        return False, "DATABASE_URL does not look like a local test database; running pytest hook normally."

    if database_is_available(url):
        return False, "Test database is available."

    return True, f"Test database is unavailable at {url}; pre-commit pytest hook should be skipped."


def main() -> int:
    should_skip, message = should_skip_pytest_hook()
    if should_skip:
        print(message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
