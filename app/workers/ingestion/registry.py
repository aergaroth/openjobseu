from typing import Dict, Callable

from app.workers.ingestion.employer import run_employer_ingestion

INGESTION_HANDLERS: Dict[str, Callable[[], dict]] = {
    "employer_ing": run_employer_ingestion,
}



def get_available_ingestion_sources() -> list[str]:
    return list(INGESTION_HANDLERS.keys())
