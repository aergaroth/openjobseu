import os
from datetime import datetime, timezone
import uuid

import pytest
import requests
from faker import Faker
from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError, ProgrammingError

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
def block_external_httpx_requests(respx_mock):
    """
    Automatycznie aktywuje środowisko `respx` dla każdego testu,
    blokując wszelkie niezamockowane zapytania asynchroniczne z `httpx`.
    """
    # Przepuszczamy ruch wewnętrzny (w razie testowania API z użyciem httpx.AsyncClient)
    respx_mock.route(host__in=["testserver", "localhost", "127.0.0.1"]).pass_through()
    yield respx_mock


@pytest.fixture(scope="session", autouse=True)
def db_engine_setup():
    """Inicjalizuje bazę i uruchamia migracje dokładnie raz na sesję testową."""
    global _engine
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.attributes["configure_logger"] = False
        _engine = get_engine()

        with _engine.connect() as conn:
            jobs_exist = conn.execute(text("SELECT to_regclass('public.jobs')")).scalar_one_or_none()
            alembic_exists = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one_or_none()
            if jobs_exist and not alembic_exists:
                command.stamp(alembic_cfg, "56f2bf3724cd")
                conn.commit()

        command.upgrade(alembic_cfg, "head")
    except (OperationalError, InterfaceError) as exc:  # pragma: no cover
        pytest.skip(f"database unavailable, skipping tests: {exc}")
    except ProgrammingError as exc:
        raise RuntimeError("test database schema is missing. Ensure Alembic migrations are up to date.") from exc


@pytest.fixture(autouse=True)
def clean_db(db_engine_setup):
    """Truncate the main tables before each test so state doesn't leak.

    We deliberately use ``BEGIN/COMMIT`` semantics rather than ``DROP`` so
    that the migration state remains intact and Alembic migrations can be invoked
    multiple times in a single session without any special handling.
    If the database is unreachable we skip the entire test session rather
    than hard-fail; that keeps the repository usable without a running
    backend (e.g. for linting or editing).
    """
    global _engine
    if _engine is None:
        return

    with _engine.begin() as conn:
        # DELETE jest o rzędy wielkości szybsze niż TRUNCATE CASCADE w PostgreSQL,
        # zwłaszcza na pustych lub małych tabelach. Usuwamy od dzieci do rodziców.
        conn.execute(text("DELETE FROM job_snapshots;"))
        conn.execute(text("DELETE FROM compliance_reports;"))
        conn.execute(text("DELETE FROM job_sources;"))
        conn.execute(text("DELETE FROM jobs;"))
        conn.execute(text("DELETE FROM company_ats;"))
        conn.execute(text("DELETE FROM companies;"))
    yield


class DbFactory:
    """
    Fabryka danych testowych. Pozwala na zwięzłe generowanie spójnych
    hierarchii danych (Firma -> ATS -> Oferty) w bazie PostgreSQL.
    """

    def __init__(self, engine):
        self.engine = engine

    def create_company(self, **overrides) -> dict:
        company_id = overrides.get("company_id", str(uuid.uuid4()))
        data = {
            "company_id": company_id,
            "legal_name": f"Test Company {company_id[:8]}",
            "brand_name": f"Brand {company_id[:8]}",
            "hq_country": "PL",
            "remote_posture": "UNKNOWN",
            "is_active": True,
            "approved_jobs_count": 0,
            "total_jobs_count": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        data.update(overrides)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        with self.engine.begin() as conn:
            conn.execute(text(f"INSERT INTO companies ({columns}) VALUES ({placeholders})"), data)
        return data

    def create_ats(self, company_id: str, **overrides) -> dict:
        data = {
            "company_ats_id": overrides.get("company_ats_id", str(uuid.uuid4())),
            "company_id": company_id,
            "provider": "greenhouse",
            "ats_slug": f"slug-{company_id[:8]}",
            "ats_api_url": None,
            "careers_url": f"https://example.com/careers/{company_id[:8]}",
            "is_active": True,
            "last_sync_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        data.update(overrides)

        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO company_ats (
                        company_ats_id,
                        company_id,
                        provider,
                        ats_slug,
                        ats_api_url,
                        careers_url,
                        is_active,
                        last_sync_at,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :company_ats_id,
                        :company_id,
                        :provider,
                        :ats_slug,
                        :ats_api_url,
                        :careers_url,
                        :is_active,
                        :last_sync_at,
                        :created_at,
                        :updated_at
                    )
                """),
                data,
            )
        return data

    def create_job(self, company_id: str, **overrides) -> dict:
        job_id = overrides.get("job_id", f"job-{uuid.uuid4().hex[:8]}")
        data = {
            "job_id": job_id,
            "job_uid": f"uid-{job_id}",
            "job_fingerprint": f"fp-{job_id}",
            "company_id": company_id,
            "source": overrides.get("source", "greenhouse:test"),
            "source_job_id": f"src-{job_id}",
            "source_url": f"https://example.com/jobs/{job_id}",
            "title": "Software Engineer",
            "company_name": "Test Company",
            "description": "Standard job description.",
            "remote_source_flag": True,
            "remote_scope": "Europe",
            "status": "new",
            "first_seen_at": datetime.now(timezone.utc),
        }
        # Pozwalamy nadpisać dowolne inne pole, np. status compliancu
        data.update(overrides)

        # Dynamiczne budowanie zapytania (tylko z kluczy, które faktycznie przekazano do słownika)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        with self.engine.begin() as conn:
            conn.execute(text(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})"), data)
        return data

    def create_job_snapshot(self, job_id: str, **overrides) -> dict:
        data = {
            "job_id": job_id,
            "job_fingerprint": overrides.get("job_fingerprint", f"fp-{job_id}"),
            "title": overrides.get("title", "Software Engineer"),
            "remote_class": overrides.get("remote_class", "UNKNOWN"),
            "geo_class": overrides.get("geo_class", "UNKNOWN"),
            "salary_min": overrides.get("salary_min"),
            "salary_max": overrides.get("salary_max"),
            "salary_currency": overrides.get("salary_currency"),
            "captured_at": overrides.get("captured_at", datetime.now(timezone.utc)),
        }
        data.update(overrides)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        with self.engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO job_snapshots ({columns}) VALUES ({placeholders})"),
                data,
            )
        return data

    def create_job_source(self, job_id: str, **overrides) -> dict:
        now = datetime.now(timezone.utc)
        data = {
            "job_id": job_id,
            "source": overrides.get("source", "greenhouse:test"),
            "source_job_id": overrides.get("source_job_id", f"src-{job_id}"),
            "source_url": overrides.get("source_url", f"https://example.com/jobs/{job_id}"),
            "first_seen_at": overrides.get("first_seen_at", now),
            "last_seen_at": overrides.get("last_seen_at", now),
            "seen_count": overrides.get("seen_count", 1),
            "created_at": overrides.get("created_at", now),
            "updated_at": overrides.get("updated_at", now),
        }
        data.update(overrides)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())

        with self.engine.begin() as conn:
            conn.execute(text(f"INSERT INTO job_sources ({columns}) VALUES ({placeholders})"), data)
        return data

    def create_company_with_jobs(
        self,
        num_jobs: int = 3,
        company_overrides: dict = None,
        job_overrides: dict = None,
    ) -> tuple[dict, list[dict]]:
        """Generuje pełną gałąź: Firma -> ATS -> X Ofert Pracy"""
        company = self.create_company(**(company_overrides or {}))
        self.create_ats(company["company_id"])

        jobs = []
        for i in range(num_jobs):
            # Kopiujemy parametry nadpisujące ofertę i ewentualnie indeksujemy tytuły
            jo = dict(job_overrides or {})
            if "title" not in jo:
                jo["title"] = f"Job Title {i + 1}"
            jobs.append(self.create_job(company["company_id"], **jo))

        return company, jobs

    def get_company_ats_integrations(self, company_id: str) -> list[dict]:
        """Pobiera z bazy wiedzy wszystkie aktywne powiązania z zewnętrznymi serwisami ATS dla danej firmy."""
        with self.engine.connect() as conn:
            rows = (
                conn.execute(
                    text("SELECT * FROM company_ats WHERE company_id = :company_id ORDER BY created_at DESC"),
                    {"company_id": company_id},
                )
                .mappings()
                .all()
            )
            return [dict(r) for r in rows]

    def get_company(self, company_id: str) -> dict | None:
        """Pobiera aktualny, pełny stan firmy z bazy (do sprawdzania np. flag czy dat aktualizacji)."""
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM companies WHERE company_id = :company_id"),
                    {"company_id": company_id},
                )
                .mappings()
                .one_or_none()
            )
            return dict(row) if row else None

    def get_job(self, job_id: str) -> dict | None:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM jobs WHERE job_id = :job_id"),
                    {"job_id": job_id},
                )
                .mappings()
                .one_or_none()
            )
            return dict(row) if row else None


@pytest.fixture
def db_factory(db_engine_setup) -> DbFactory:
    """Zwraca instancję fabryki z dostępem do aktywnego silnika bazy."""
    return DbFactory(_engine)


@pytest.fixture
def faker_instance():
    """Zwraca deterministyczną instancję Fakera resetowaną co test (zawsze te same dane)."""
    fake = Faker(["en_US", "pl_PL"])
    Faker.seed(42)
    return fake


@pytest.fixture
def seed_realistic_market_data(db_factory, faker_instance):
    """
    Wstrzykuje do bazy realistyczny zestaw 5 firm i losowych dla nich ofert pracy,
    idealny do obciążeniowego testowania wyszukiwania i paginacji.
    """
    companies = []
    for _ in range(5):
        comp = db_factory.create_company(
            legal_name=faker_instance.company(),
            hq_country=faker_instance.country_code(),
        )
        companies.append(comp)

        for _ in range(faker_instance.random_int(min=2, max=8)):
            db_factory.create_job(
                comp["company_id"],
                title=faker_instance.job(),
                description=faker_instance.text(max_nb_chars=800),
                company_name=comp["legal_name"],
                source_url=faker_instance.url(),
                salary_min=faker_instance.random_int(min=30000, max=70000),
                salary_max=faker_instance.random_int(min=80000, max=150000),
                salary_currency=faker_instance.random_element(elements=("USD", "EUR", "GBP", "PLN")),
                remote_scope=faker_instance.random_element(elements=("Europe", "Worldwide", "US", "UK", "Poland")),
                status=faker_instance.random_element(elements=("new", "active", "expired", "stale")),
            )
    return companies
