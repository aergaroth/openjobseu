from fastapi import FastAPI
from datetime import datetime, timezone
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from storage.db import get_engine, db_healthcheck
from storage.sqlite import init_db
from app.workers.compliance_resolution import (
    run_compliance_resolution_for_existing_db,
)
from app.internal import router as internal_router
from app.api.jobs import router as jobs_router
from app.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)
logger.info("logging configured")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()

    # --- DB bootstrap ---
    try:
        init_db()
        db_healthcheck()
    except Exception as e:
        logger.exception("DB bootstrap failed")


    try:
        run_compliance_resolution_for_existing_db()
    except Exception:
        logger.exception("initial compliance bootstrap failed")

    yield

    # --- Graceful shutdown ---
    engine.dispose()


app = FastAPI(
    title="OpenJobsEU Runtime",
    version="0.1.0",
    lifespan=lifespan,
)


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
    return {"ready": True}