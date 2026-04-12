from unittest.mock import MagicMock

from app.workers.discovery.dorking import _extract_slug_from_url, run_dorking_discovery
import app.workers.discovery.dorking as dorking_module


def test_extract_slug_from_url_subdomain_based():
    # Personio
    assert _extract_slug_from_url("https://test-company.jobs.personio.com/job/123", "personio") == "test-company"
    assert _extract_slug_from_url("https://another-slug.jobs.personio.de", "personio") == "another-slug"

    # Recruitee
    assert _extract_slug_from_url("https://acme-inc.recruitee.com/o/developer", "recruitee") == "acme-inc"
    assert _extract_slug_from_url("https://my-startup.recruitee.com", "recruitee") == "my-startup"

    # Traffit
    assert _extract_slug_from_url("https://acme-inc.traffit.com/public/an/abc", "traffit") == "acme-inc"
    assert _extract_slug_from_url("https://my-startup.traffit.com", "traffit") == "my-startup"


def test_extract_slug_from_url_path_based():
    # Lever
    assert _extract_slug_from_url("https://jobs.lever.co/lever-inc/xyz-123", "lever") == "lever-inc"
    assert _extract_slug_from_url("https://jobs.lever.co/acme", "lever") == "acme"

    # Greenhouse
    assert _extract_slug_from_url("https://boards.greenhouse.io/greenhouse-test", "greenhouse") == "greenhouse-test"
    assert _extract_slug_from_url("https://boards.greenhouse.io/acme/jobs/123", "greenhouse") == "acme"

    # Ashby
    assert _extract_slug_from_url("https://jobs.ashbyhq.com/ashby-co/123", "ashby") == "ashby-co"

    # Workable
    assert _extract_slug_from_url("https://apply.workable.com/workable-corp/j/456", "workable") == "workable-corp"


def test_extract_slug_from_url_invalid_or_empty():
    # Brak hosta / błędny format
    assert _extract_slug_from_url("not-a-url", "personio") is None

    # Puste ścieżki
    assert _extract_slug_from_url("https://boards.greenhouse.io/", "greenhouse") is None
    assert _extract_slug_from_url("https://jobs.lever.co", "lever") is None

    # Nieobsługiwany provider fallback (nie pasuje do subdomen ani ścieżek zdefiniowanych w ifach)
    assert _extract_slug_from_url("https://jobs.unknown.com/slug", "unknown_provider") is None


def test_extract_slug_from_url_jobadder():
    assert _extract_slug_from_url("https://app.jobadder.com/jobboard/abc-123", "jobadder") == "abc-123"
    assert (
        _extract_slug_from_url(
            "https://app.jobadder.com/jobboard/6e8f3a2b-4c1d-4e5f-9012-3456789abcde",
            "jobadder",
        )
        == "6e8f3a2b-4c1d-4e5f-9012-3456789abcde"
    )
    # Brak board ID w ścieżce → None
    assert _extract_slug_from_url("https://app.jobadder.com/jobboard/", "jobadder") is None
    # Zły prefix ścieżki → None
    assert _extract_slug_from_url("https://app.jobadder.com/other/abc-123", "jobadder") is None


def test_run_dorking_discovery_success_path(monkeypatch):
    mock_list_providers = MagicMock(return_value=["greenhouse", "unknown"])

    class MockGreenhouseAdapter:
        dorking_target = "boards.greenhouse.io"

    class MockUnknownAdapter:
        dorking_target = None

    def mock_get_adapter(provider):
        if provider == "greenhouse":
            return MockGreenhouseAdapter()
        return MockUnknownAdapter()

    mock_google_search = MagicMock()
    # Symulujemy: strona 1 ma dwa różne wyniki, strona 2 ma duplikat z pierwszej strony + coś nowego, strona 3 jest pusta
    mock_google_search.side_effect = [
        [
            "https://boards.greenhouse.io/companyA/jobs/1",
            "https://boards.greenhouse.io/companyB",
        ],
        [
            "https://boards.greenhouse.io/companyA/jobs/2",
            "https://boards.greenhouse.io/companyC/jobs/9",
        ],
        [],
    ]

    mock_insert = MagicMock()

    # Kontekst DB
    class DummyConn:
        pass

    class DummyEngine:
        def begin(self):
            class DummyCtx:
                def __enter__(self):
                    return DummyConn()

                def __exit__(self, *args):
                    pass

            return DummyCtx()

    monkeypatch.setattr(dorking_module, "list_providers", mock_list_providers)
    monkeypatch.setattr(dorking_module, "get_adapter", mock_get_adapter)
    monkeypatch.setattr(dorking_module, "google_custom_search", mock_google_search)
    monkeypatch.setattr(dorking_module, "get_engine", lambda: DummyEngine())
    monkeypatch.setattr(dorking_module, "insert_discovered_slugs", mock_insert)

    mock_sleep = MagicMock()
    monkeypatch.setattr(dorking_module.time, "sleep", mock_sleep)

    result = run_dorking_discovery()

    # Sprawdzamy stan wykonania
    assert result["status"] == "ok"

    # Oczekujemy wyłapania 3 unikalnych slugów pomimo że `companyA` wystąpiło 2 razy
    assert result["discovered_slugs"] == 3

    # Weryfikacja bazy danych
    mock_insert.assert_called_once()
    inserted_data = mock_insert.call_args[0][1]
    assert len(inserted_data) == 3

    slugs = {item["slug"] for item in inserted_data}
    assert slugs == {"companyA", "companyB", "companyC"}
    for item in inserted_data:
        assert item["provider"] == "greenhouse"
        assert item["discovery_source"] == "dorking"

    # Weryfikacja zapytań do Google
    assert mock_google_search.call_count == 3
    mock_google_search.assert_any_call('site:boards.greenhouse.io "Europe"', num_results=10, start=1)
    mock_google_search.assert_any_call('site:boards.greenhouse.io "Europe"', num_results=10, start=11)
    mock_google_search.assert_any_call('site:boards.greenhouse.io "Europe"', num_results=10, start=21)

    # Weryfikacja throttling'u (2 strony z wynikami wywołują sleep + 1 pauza po zakończeniu providera)
    assert mock_sleep.call_count == 3


def test_run_dorking_discovery_google_api_error(monkeypatch):
    mock_list_providers = MagicMock(return_value=["greenhouse"])

    class MockGreenhouseAdapter:
        dorking_target = "boards.greenhouse.io"

    monkeypatch.setattr(dorking_module, "list_providers", mock_list_providers)
    monkeypatch.setattr(dorking_module, "get_adapter", lambda p: MockGreenhouseAdapter())

    # Symulujemy nagłą awarię API (np. wyczerpanie dziennego limitu Google Custom Search)
    monkeypatch.setattr(dorking_module, "google_custom_search", MagicMock(side_effect=RuntimeError("Quota exceeded")))

    # Upewniamy się, że środowisko potrafi bezpiecznie złapać wyjątek z API bez wysadzania całego Workera
    result = run_dorking_discovery()

    # Status zazwyczaj zależy od implementacji logiki obsługi błędu w dorking.py,
    # najistotniejsze jest to, żeby funkcja zwróciła słownik metryk, a nie spowodowała hard-crash.
    assert "status" in result
    assert result.get("discovered_slugs", 0) == 0


def test_dorking_handles_google_api_quota_exhaustion(monkeypatch):
    """Simulate Google Custom Search API quotas in dorking."""
    from app.workers.discovery import dorking

    def mock_search(*args, **kwargs):
        raise Exception("Quota exceeded for quota metric")

    monkeypatch.setattr(dorking, "google_custom_search", mock_search)

    result = dorking.run_dorking_discovery()
    assert result["status"] == "ok"
