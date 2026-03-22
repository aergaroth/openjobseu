from unittest.mock import MagicMock
from app.workers.discovery.careers_crawler import (
    _fetch_careers_page,
    run_careers_discovery,
)
import app.workers.discovery.careers_crawler as crawler_module


def test_fetch_careers_page(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"<html>data</html>"]
    mock_resp.url = "https://example.com/careers"
    monkeypatch.setattr(crawler_module.requests, "get", lambda *a, **kw: mock_resp)

    resp = _fetch_careers_page("https://example.com/careers")
    assert resp is not None
    assert resp._content == b"<html>data</html>"


def test_fetch_careers_page_invalid_url():
    assert _fetch_careers_page(None) is None
    assert _fetch_careers_page("ftp://example.com") is None


def test_fetch_careers_page_exception(monkeypatch):
    import requests

    monkeypatch.setattr(
        crawler_module.requests,
        "get",
        MagicMock(side_effect=requests.RequestException("Fail")),
    )
    assert _fetch_careers_page("https://example.com/careers") is None


def test_run_careers_discovery_empty(monkeypatch):
    monkeypatch.setattr(crawler_module, "load_discovery_companies", lambda *a, **kw: [])

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

    monkeypatch.setattr(crawler_module, "get_engine", lambda: DummyEngine())
    assert run_careers_discovery()["companies_scanned"] == 0


def test_is_valid_slug():
    assert crawler_module._is_valid_slug("valid-slug") is True
    assert crawler_module._is_valid_slug("ab") is False  # Zbyt krótki
    assert crawler_module._is_valid_slug("demo-slug") is False  # Zawiera zakazane słowo "demo"
    assert crawler_module._is_valid_slug("careers") is False  # Zawiera zakazane słowo "careers"


def test_detect_provider():
    assert crawler_module._detect_provider("https://boards.greenhouse.io/acme") == (
        "greenhouse",
        "acme",
    )
    assert crawler_module._detect_provider("https://boards.greenhouse.io/embed/job_board?for=acme") == (
        "greenhouse",
        "acme",
    )
    assert crawler_module._detect_provider("https://jobs.lever.co/lever-slug") == (
        "lever",
        "lever-slug",
    )
    assert crawler_module._detect_provider("https://example.com/jobs") is None


def test_extract_candidate_links():
    html = """
    <html>
        <body>
            <a href="/careers">Careers</a>
            <a href="/about">About us</a>
            <a href="https://example.com/open-positions">Open Positions</a>
        </body>
    </html>
    """
    links = crawler_module._extract_candidate_links(html, "https://mysite.com")
    assert len(links) == 2
    assert "https://mysite.com/careers" in links
    assert "https://example.com/open-positions" in links
    assert "https://mysite.com/about" not in links


def test_detect_provider_from_redirects():
    mock_resp = MagicMock()
    mock_resp.url = "https://example.com/careers"

    mock_history = MagicMock()
    mock_history.url = "https://boards.greenhouse.io/redirect-slug"
    mock_resp.history = [mock_history]

    assert crawler_module._detect_provider_from_redirects(mock_resp) == (
        "greenhouse",
        "redirect-slug",
    )


def test_run_careers_discovery_happy_path(monkeypatch):
    mock_row = {"company_id": "123", "careers_url": "https://example.com/careers"}
    monkeypatch.setattr(crawler_module, "load_discovery_companies", lambda *a, **kw: [mock_row])

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

    monkeypatch.setattr(crawler_module, "get_engine", lambda: DummyEngine())

    mock_resp = MagicMock()
    mock_resp.url = "https://example.com/careers"
    mock_resp.text = "<html>some content</html>"
    mock_resp.history = []
    monkeypatch.setattr(crawler_module, "_fetch_careers_page", lambda url: mock_resp)
    monkeypatch.setattr(
        crawler_module,
        "_detect_provider_from_redirects",
        lambda r: ("lever", "acme-corp"),
    )
    monkeypatch.setattr(
        crawler_module,
        "probe_ats",
        lambda p, s: {
            "jobs_total": 2,
            "remote_hits": 1,
            "recent_job_at": "2026-03-01T00:00:00Z",
        },
    )

    monkeypatch.setattr(crawler_module, "insert_discovered_company_ats", lambda *a, **kw: True)
    monkeypatch.setattr(crawler_module, "update_discovery_last_checked_at", lambda *a, **kw: None)

    metrics = crawler_module.run_careers_discovery()

    assert metrics["companies_scanned"] == 1
    assert metrics["ats_detected"] == 1
    assert metrics["ats_probed"] == 1
    assert metrics["ats_inserted"] == 1
