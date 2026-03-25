from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.workers.discovery import ats_guessing
from app.workers.discovery.ats_guessing import run_ats_guessing, _is_recent


def test_ats_guessing_date_parsing_edge_cases():
    """Test edge cases for date parsing in ats_guessing."""

    # Puste wartości i błędne formaty domyślnie przepuszczamy (jako recent)
    assert _is_recent("") is True
    assert _is_recent(None) is True
    assert _is_recent("invalid-date-string") is True

    # Skrajne przypadki wykraczające poza kalendarz rzucają ValueError, więc przepuszczamy
    assert _is_recent("2026-99-99T00:00:00Z") is True

    # Prawidłowa obsługa starej daty (powinna zostać odrzucona)
    old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
    assert _is_recent(old_date) is False

    # Sprawdza zachowanie dla dat bez tzinfo
    dt_naive = datetime.now() - timedelta(days=10)
    assert _is_recent(dt_naive) is True


@patch("app.workers.discovery.ats_guessing.get_engine")
@patch("app.workers.discovery.ats_guessing.load_discovery_companies")
def test_run_ats_guessing_row_parsing(mock_load, mock_get_engine, monkeypatch):
    class MockRowTuple(tuple):
        @property
        def company_id(self):
            return "2"

        @property
        def brand_name(self):
            return "B"

        @property
        def careers_url(self):
            return "url"

    mock_load.return_value = [
        {"company_id": "1", "brand_name": "A", "careers_url": "url"},
        MockRowTuple(["2", "B", "url"]),
    ]
    monkeypatch.setattr(ats_guessing, "PROVIDERS_TO_PROBE", [])
    monkeypatch.setattr(ats_guessing, "update_discovery_last_checked_at", MagicMock())
    res = run_ats_guessing()
    assert res["companies_scanned"] == 2


@patch("app.workers.discovery.ats_guessing.get_engine")
@patch("app.workers.discovery.ats_guessing.load_discovery_companies")
@patch("app.workers.discovery.ats_guessing.probe_ats")
@patch("app.workers.discovery.ats_guessing.insert_discovered_company_ats")
def test_run_ats_guessing_exceptions_and_duplicates(mock_insert, mock_probe, mock_load, mock_engine, monkeypatch):
    mock_load.return_value = [{"company_id": "1", "brand_name": "Acme", "careers_url": "url"}]
    monkeypatch.setattr(ats_guessing, "PROVIDERS_TO_PROBE", ["lever", "greenhouse", "workable"])
    monkeypatch.setattr(ats_guessing, "update_discovery_last_checked_at", MagicMock())

    def mock_probe_side_effect(provider, slug):
        if provider == "lever":
            raise Exception("Probe failed network timeout")
        if provider == "greenhouse":
            return {"jobs_total": "invalid", "remote_hits": "invalid", "recent_job_at": None}
        if provider == "workable":
            return {"jobs_total": 5, "remote_hits": 2, "recent_job_at": datetime.now(timezone.utc)}
        return None

    mock_probe.side_effect = mock_probe_side_effect
    # Symulujemy próbę wstawienia zduplikowanego ATS-a do bazy, co powinno objawić się flagą 'ats_duplicates'
    mock_insert.return_value = False
    res = run_ats_guessing()
    assert res["companies_scanned"] == 1
    assert res["ats_detected"] >= 1
    assert res.get("ats_duplicates", 0) == 1
