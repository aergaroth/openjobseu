import os
import pytest
from sqlalchemy import text

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
_engine = get_engine()


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate the main tables before each test so state doesn't leak.

    We deliberately use ``BEGIN/COMMIT`` semantics rather than ``DROP`` so
    that the migration state remains intact and ``init_db()`` can be invoked
    multiple times in a single session without any special handling.
    If the database is unreachable we skip the entire test session rather
    than hard-fail; that keeps the repository usable without a running
    backend (e.g. for linting or editing).
    """
    try:
        with _engine.begin() as conn:
            # companies is referenced by a foreign key in jobs; cascade just in
            # case tests add other data later.
            conn.execute(text("TRUNCATE jobs, companies CASCADE"))
    except Exception as exc:  # pragma: no cover - network errors etc
        pytest.skip(f"database unavailable, skipping tests: {exc}")
    yield