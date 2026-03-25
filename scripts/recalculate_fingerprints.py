import logging
import sys
import os

# Zapewnienie dostępu do modułów projektu
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from storage.db_engine import get_engine

# Założyłem ścieżkę do funkcji; upewnij się, że jest poprawna dla Twojego projektu.
from app.domain.jobs.job_processing import compute_job_fingerprint

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    engine = get_engine()

    logger.info("Pobieranie ofert pracy z bazy...")
    with engine.connect() as conn:
        # Pobieramy pola i sortujemy po first_seen_at, aby zachować najstarszą ofertę jako oryginał
        result = conn.execute(
            text("""
            SELECT job_id, job_fingerprint, title, company_name, description 
            FROM jobs 
            ORDER BY first_seen_at ASC
        """)
        )
        rows = result.mappings().all()

    logger.info(f"Pobrano {len(rows)} ofert. Przeliczanie fingerprintów...")

    seen_fps = set()
    update_data = []
    delete_data = []

    for row in rows:
        # Generujemy nowy fingerprint na bazie zaktualizowanego, czystego opisu
        new_fp = compute_job_fingerprint(
            title=row["title"], company_name=row["company_name"], description=row["description"]
        )

        if new_fp in seen_fps:
            # Znaleziono duplikat - oznaczamy do usunięcia
            delete_data.append({"job_id": row["job_id"]})
        else:
            # Unikalna oferta - dodajemy do zbioru widzianych
            seen_fps.add(new_fp)
            # Dodajemy do aktualizacji, tylko jeśli fingerprint faktycznie się zmienił
            if new_fp != row["job_fingerprint"]:
                update_data.append({"job_id": row["job_id"], "new_fp": new_fp})

    if not update_data and not delete_data:
        logger.info("Brak danych do aktualizacji i usunięcia.")
        return

    with engine.begin() as begin_conn:
        if delete_data:
            logger.info(f"Usuwanie {len(delete_data)} zdemaskowanych duplikatów...")
            begin_conn.execute(text("DELETE FROM jobs WHERE job_id = :job_id"), delete_data)

        if update_data:
            logger.info(f"Zapisywanie {len(update_data)} nowych fingerprintów do bazy (Bulk Update)...")
            begin_conn.execute(text("UPDATE jobs SET job_fingerprint = :new_fp WHERE job_id = :job_id"), update_data)

    logger.info("Gotowe! Baza jest w 100% spójna, wolna od duplikatów i gotowa na nowe pobrania.")


if __name__ == "__main__":
    main()
