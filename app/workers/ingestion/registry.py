from typing import Dict, Callable

from ingestion.adapters.greenhouse_api import GREENHOUSE_BOARDS

from app.workers.ingestion.weworkremotely import run_weworkremotely_ingestion
from app.workers.ingestion.remotive import run_remotive_ingestion
from app.workers.ingestion.remoteok import run_remoteok_ingestion
from app.workers.ingestion.greenhouse import run_greenhouse_ingestion

INGESTION_HANDLERS: Dict[str, Callable[[], dict]] = {
    "weworkremotely": run_weworkremotely_ingestion,
    "remotive": run_remotive_ingestion,
    "remoteok": run_remoteok_ingestion,
}

# for token in GREENHOUSE_BOARDS:
#     INGESTION_HANDLERS[f"greenhouse:{token}"] = (
#         lambda token=token: run_greenhouse_ingestion(token)
#     )


def get_available_ingestion_sources() -> list[str]:
    return list(INGESTION_HANDLERS.keys())
