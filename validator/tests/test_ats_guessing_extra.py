from datetime import datetime, timezone, timedelta

from app.workers.discovery import ats_guessing


def test_ats_guessing_date_parsing_edge_cases():
    """Test edge cases for date parsing in ats_guessing."""

    # Puste wartości i błędne formaty domyślnie przepuszczamy (jako recent)
    assert ats_guessing._is_recent("") is True
    assert ats_guessing._is_recent(None) is True
    assert ats_guessing._is_recent("invalid-date-string") is True

    # Skrajne przypadki wykraczające poza kalendarz rzucają ValueError, więc przepuszczamy
    assert ats_guessing._is_recent("2026-99-99T00:00:00Z") is True

    # Prawidłowa obsługa starej daty (powinna zostać odrzucona)
    old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
    assert ats_guessing._is_recent(old_date) is False
