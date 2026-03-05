from fastapi import FastAPI, Response, status
from datetime import datetime, timezone
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from storage.db_engine import get_engine, db_healthcheck
from storage.db_logic import init_db
from app.internal import router as internal_router
from app.api.jobs import router as jobs_router
from app.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)
logger.info("logging configured")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    engine = get_engine()

    # --- DB bootstrap ---
    try:
        init_db()
        db_healthcheck()
    except Exception:
        logger.exception("DB bootstrap failed")
        raise

    app.state.ready = True
    logger.info("DB bootstrap completed")
    yield

    # --- Graceful shutdown ---
    app.state.ready = False
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
def ready(response: Response):
    is_ready = bool(getattr(app.state, "ready", False))
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": is_ready}
