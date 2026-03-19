import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from app.workers.discovery.ats_reverse import _load_slugs, _is_recent
import app.workers.discovery.ats_reverse as reverse_module

def test_load_slugs_default(monkeypatch):
    monkeypatch.delenv("ATS_REVERSE_SLUGS_URL", raising=False)
    slugs = _load_slugs()
    assert "stripe" in slugs
    assert "notion" in slugs
    assert "gitlab" in slugs

def test_load_slugs_external(monkeypatch):
    monkeypatch.setenv("ATS_REVERSE_SLUGS_URL", "http://example.com/slugs.txt")
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"slug1\nslug2\n#comment\n"]
    monkeypatch.setattr(reverse_module.requests, "get", lambda *a, **kw: mock_resp)

    slugs = _load_slugs()
    # Sprawdzamy, czy wczytuje z zewnątrz i ignoruje komentarze
    assert "slug1" in slugs
    assert "slug2" in slugs
    assert "#comment" not in slugs
    
def test_is_recent():
    now = datetime.now(timezone.utc)
    assert _is_recent(None) is True
    
    # 10 dni temu - jest w ramach limitu 120 dni (True)
    assert _is_recent((now - timedelta(days=10)).isoformat()) is True
    # Pół roku temu - poza limitem (False)
    assert _is_recent((now - timedelta(days=150)).isoformat()) is False