import zipfile
import io
import requests
from unittest.mock import MagicMock
from app.workers.discovery.company_sources import (
    _guess_careers,
    _fetch_github_remote_companies,
    run_company_source_discovery,
)
import app.workers.discovery.company_sources as cs_module


def test_guess_careers():
    urls = _guess_careers("https://example.com/")
    assert "https://example.com/careers" in urls
    assert "https://example.com/jobs" in urls


def test_fetch_github_remote_companies(monkeypatch):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        content = 'title: "Acme Corp"\nwebsite: "https://acme.com"'
        zf.writestr("remote-jobs-main/src/companies/acme.md", content)
        zf.writestr("remote-jobs-main/src/companies/ignore.txt", "ignore")

    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [zip_buffer.getvalue()]
    mock_resp.raise_for_status = MagicMock()

    monkeypatch.setattr(cs_module.requests, "get", lambda *a, **kw: mock_resp)

    companies = _fetch_github_remote_companies()
    assert len(companies) == 1
    assert companies[0]["name"] == "Acme Corp"
    assert companies[0]["url"] == "https://acme.com"


def test_fetch_github_remote_companies_network_error(monkeypatch):
    # Symulujemy niedostępność GitHuba
    monkeypatch.setattr(
        cs_module.requests, "get", MagicMock(side_effect=requests.RequestException("Connection refused"))
    )
    # Zabezpieczenie przed rzuceniem błędem dalej w stos aplikacji
    companies = _fetch_github_remote_companies()
    assert companies == []


def test_run_company_source_discovery(monkeypatch):
    monkeypatch.setattr(
        cs_module,
        "_fetch_github_remote_companies",
        lambda: [
            {"name": "NewCo", "url": "https://newco.com"},
            {"name": "ExistingCo", "url": "https://existing.com"},
        ],
    )

    class DummyConn:
        pass

    class DummyCtx:
        def __enter__(self):
            return DummyConn()

        def __exit__(self, *args):
            pass

    class DummyEngine:
        def connect(self):
            return DummyCtx()

        def begin(self):
            return DummyCtx()

    monkeypatch.setattr(cs_module, "get_engine", lambda: DummyEngine())
    monkeypatch.setattr(cs_module, "get_existing_brand_names", lambda conn: {"existingco"})

    inserted = []
    monkeypatch.setattr(
        cs_module,
        "insert_source_company",
        lambda conn, name, careers_url: inserted.append(name) or True,
    )

    mock_head = MagicMock()
    mock_head.ok = True
    mock_head.url = "https://newco.com/careers"
    monkeypatch.setattr(cs_module.requests, "head", lambda *a, **kw: mock_head)

    metrics = run_company_source_discovery()
    assert metrics["companies_found"] == 2
    assert metrics["companies_skipped"] == 1
    assert metrics["companies_inserted"] == 1


def test_run_company_source_discovery_head_timeout(monkeypatch):
    # Sprawdzenie zachowania kiedy strona firmy odpowiada bardzo wolno (timeout)
    monkeypatch.setattr(
        cs_module,
        "_fetch_github_remote_companies",
        lambda: [{"name": "TimeoutCo", "url": "https://timeout.com"}],
    )

    class DummyCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        cs_module, "get_engine", lambda: MagicMock(connect=lambda: DummyCtx(), begin=lambda: DummyCtx())
    )
    monkeypatch.setattr(cs_module, "get_existing_brand_names", lambda conn: set())

    # Rzucamy Timeout podczas próby sprawdzenia adresu careers_url
    monkeypatch.setattr(cs_module.requests, "head", MagicMock(side_effect=requests.Timeout("Read timeout")))

    metrics = run_company_source_discovery()

    assert metrics["companies_found"] == 1
    assert metrics["companies_inserted"] == 0
