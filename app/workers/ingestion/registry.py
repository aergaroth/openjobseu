from typing import Dict, Callable

from app.workers.ingestion.weworkremotely import run_weworkremotely_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.ingestion.remoteok import run_remoteok_ingestion


INGESTION_HANDLERS: Dict[str, Callable[[], dict]] = {
    "weworkremotely": run_weworkremotely_ingestion,
    "remotive": run_remotive_ingestion,
    "remoteok": run_remoteok_ingestion,
}


def get_available_ingestion_sources() -> list[str]:
    return list(INGESTION_HANDLERS.keys())
