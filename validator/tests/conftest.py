import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError, ProgrammingError
import requests

# tests should run against PostgreSQL rather than SQLite.  the CI workflow
# already exports a suitable `DATABASE_URL`; when running locally you can
# either set that yourself or run `docker compose up -d postgres` (or
# something similar) to provide a database.  default to the same URL used by
# GitHub Actions so things work out of the box in most development
# environments.

os.environ.setdefault("DB_MODE", "standard")

# SAFETY: be explicit about which database we're connecting to.  using
# setdefault() is too permissive—if DATABASE_URL is already in the environment
# pointing at production, we *must* detect that and refuse to run tests.
# setdefault only sets the value if unset, so production URLs would slip through
# and get truncated when tests run.
_default_test_url = "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = _default_test_url
else:
    # DATABASE_URL is already set; verify it looks like a test database
    # to prevent accidentally wiping production data.
    db_url = os.environ["DATABASE_URL"]
    safe_indicators = {
        "localhost",
        "127.0.0.1",
        "testdb",
        "test",
        ":5432",  # default postgres port is unusual in prod, usually firewalled
    }
    if not any(ind in db_url for ind in safe_indicators):
        raise RuntimeError(
            f"DATABASE_URL does not appear to be a test database: {db_url}. "
            "Refusing to run tests to avoid data loss. "
            "Unset DATABASE_URL or point it at a test instance."
        )

# if any modules create an engine at import time we want it pointed at the
# right database; grab it now so the fixture below can reset state easily.
from storage.db_engine import get_engine
from alembic import command
from alembic.config import Config

_engine = None


@pytest.fixture(autouse=True)
def block_external_requests(monkeypatch):
    """
    Blokuje wszelkie prawdziwe zapytania HTTP do sieci podczas testów.
    Dzięki temu, jeśli brakuje mocka, test od razu wybuchnie błędem,
    zamiast wchodzić w minuty czekania lub zakleszczać bazę w tle!
    """
    original_request = requests.Session.request

    def mock_request(self, method, url, *args, **kwargs):
        # Pozwalamy tylko na żądania wewnętrzne z TestClient (FastAPI)
        if str(url).startswith(("http://testserver", "http://localhost", "http://127.0.0.1")):
            return original_request(self, method, url, *args, **kwargs)
        
        raise RuntimeError(f"NIEZAMOCKOWANE ZAPYTANIE SIECIOWE W TEŚCIE: {method} {url}")

    monkeypatch.setattr(requests.Session, "request", mock_request)

@pytest.fixture(autouse=True)
def clean_db():
    """Truncate the main tables before each test so state doesn't leak.

    We deliberately use ``BEGIN/COMMIT`` semantics rather than ``DROP`` so
    that the migration state remains intact and Alembic migrations can be invoked
    multiple times in a single session without any special handling.
    If the database is unreachable we skip the entire test session rather
    than hard-fail; that keeps the repository usable without a running
    backend (e.g. for linting or editing).
    """
    global _engine
    try:
        if _engine is None:
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.attributes["configure_logger"] = False
            _engine = get_engine()

            # Auto-adopt legacy test database
            with _engine.connect() as conn:
                jobs_exist = conn.execute(text("SELECT to_regclass('public.jobs')")).scalar_one_or_none()
                alembic_exists = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one_or_none()
                if jobs_exist and not alembic_exists:
                    command.stamp(alembic_cfg, "56f2bf3724cd")
                    conn.commit()

            command.upgrade(alembic_cfg, "head")
        with _engine.begin() as conn:
            conn.execute(text("TRUNCATE jobs, companies CASCADE"))
    except (OperationalError, InterfaceError) as exc:  # pragma: no cover - network/auth errors etc
        pytest.skip(f"database unavailable, skipping tests: {exc}")
    except ProgrammingError as exc:
        raise RuntimeError(
            "test database schema is missing (e.g. table 'jobs' or 'companies'). "
            "Ensure Alembic migrations are up to date."
        ) from exc
    yield
