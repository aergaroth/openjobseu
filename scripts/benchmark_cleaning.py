import json
import os
import sys
import time
import logging

# Zapewnienie dostępu do modułów projektu
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Upewnij się, że ten import prowadzi do Twojej funkcji clean_html
from app.domain.jobs.cleaning import clean_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("Ładowanie danych z jobs.json...")
    with open("jobs.json", "r", encoding="utf-8") as f:
        jobs = json.load(f)

    html_descriptions = [job["description"] for job in jobs if job.get("description")]
    logger.info(f"Pobrano {len(html_descriptions)} opisów HTML do testów.")

    iterations = 20
    logger.info(f"Rozpoczynamy testowanie... (ilość iteracji: {iterations})")

    start_time = time.time()
    for _ in range(iterations):
        for html in html_descriptions:
            clean_html(html)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time_per_desc = (total_time / (len(html_descriptions) * iterations)) * 1000

    logger.info(f"Całkowity czas ({iterations} iteracji): {total_time:.3f} sekund")
    logger.info(f"Średni czas czyszczenia JEDNEJ oferty: {avg_time_per_desc:.3f} milisekund")


if __name__ == "__main__":
    main()
