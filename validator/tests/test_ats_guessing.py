import threading
from unittest.mock import MagicMock

from app.workers.discovery.ats_guessing import run_ats_guessing
import app.workers.discovery.ats_guessing as ats_guessing


def test_run_ats_guessing_concurrent_short_circuit(monkeypatch):
    # Konfigurujemy wąski zestaw providerów, żeby upewnić się, czy działa short-circuit (wczesne wyjście z pętli)
    monkeypatch.setattr(ats_guessing, "PROVIDERS_TO_PROBE", ["lever", "greenhouse"])

    # Tworzymy mocka bazy danych symulującego firmę oczekującą na odgadnięcie ATS
    mock_companies = [
        {
            "company_id": "test-uuid-123",
            "legal_name": "Acme Corp",
            "brand_name": "Acme",
            "careers_url": "https://acme.com/careers"
        }
    ]
    monkeypatch.setattr(ats_guessing, "load_discovery_companies", lambda *args, **kwargs: mock_companies)

    # Thread-safe mock dla probe_ats (wywoływany wielowątkowo)
    probed_calls = []
    lock = threading.Lock()

    def mock_probe_ats(provider, slug):
        with lock:
            probed_calls.append((provider, slug))
        
        # Symulujemy, że znajdujemy poprawne oferty dla dostawcy Lever i sluga 'acme'
        if provider == "lever" and slug == "acme":
            return {"jobs_total": 10, "remote_hits": 5, "recent_job_at": None}
        return None

    monkeypatch.setattr(ats_guessing, "probe_ats", mock_probe_ats)

    # Mockowanie transakcji do bazy danych
    class DummyConn: pass
    class DummyCtx:
        def __enter__(self): return DummyConn()
        def __exit__(self, *args): pass
    class DummyEngine:
        def connect(self): return DummyCtx()
        def begin(self): return DummyCtx()

    monkeypatch.setattr(ats_guessing, "get_engine", lambda: DummyEngine())

    # Weryfikacja zapisu poprawnego ATS do bazy
    inserted_data = []
    def mock_insert(conn, company_id, provider, ats_slug, careers_url):
        with lock:
            inserted_data.append({"provider": provider, "slug": ats_slug})
        return True
        
    monkeypatch.setattr(ats_guessing, "insert_discovered_company_ats", mock_insert)
    
    # Ignorujemy update czasu (wywoływany w bloku finally)
    monkeypatch.setattr(ats_guessing, "update_discovery_last_checked_at", lambda *args, **kwargs: None)

    # Uruchamiamy testowanego workera
    metrics = run_ats_guessing()

    # Weryfikacja metryk
    assert metrics["companies_scanned"] == 1
    assert metrics["ats_detected"] == 1
    assert metrics["ats_inserted"] == 1
    assert metrics.get("ats_duplicates", 0) == 0

    # Weryfikujemy, że poprawnie zapisano trafienie
    assert len(inserted_data) == 1
    assert inserted_data[0]["provider"] == "lever"
    assert inserted_data[0]["slug"] == "acme"

    # Dzięki "short-circuit" po wyciągnięciu poprawnego API z "lever", 
    # pętla providerów powina zostać przerwana. Wątki dla "greenhouse" NIE powinny w ogóle zostać odpalone.
    greenhouse_calls = [c for c in probed_calls if c[0] == "greenhouse"]
    assert len(greenhouse_calls) == 0