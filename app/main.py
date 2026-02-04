from fastapi import FastAPI
from datetime import datetime, timezone
import logging

from app.internal import router as internal_router
from app.logging import configure_logging

from app.api.jobs import router as jobs_router

from storage.sqlite import init_db
from fastapi.middleware.cors import CORSMiddleware

init_db()



configure_logging()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OpenJobsEU Runtime", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://openjobseu.org"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(internal_router)
app.include_router(jobs_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    return {
        "ready": True
    }
