import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import logging
import os

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from storage.db_engine import get_engine, db_healthcheck
from storage.db_logic import init_db
from app.internal import router as internal_router
from app.api.jobs import router as jobs_router
from app.security.auth import auth_router, configure_oauth
from app.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)
logger.info("logging configured")


BOOTSTRAP_RETRY_DELAY_SECONDS = 2.0
READINESS_EXEMPT_PATHS = {"/health", "/ready"}


def _run_db_bootstrap_once() -> None:
    init_db()
    db_healthcheck()


async def _bootstrap_db_until_ready(app: FastAPI) -> None:
    attempt = 0
    while True:
        attempt += 1
        try:
            await asyncio.to_thread(_run_db_bootstrap_once)
        except Exception:
            app.state.ready = False
            logger.exception("DB bootstrap failed", extra={"attempt": attempt})
            await asyncio.sleep(BOOTSTRAP_RETRY_DELAY_SECONDS)
            continue

        app.state.ready = True
        logger.info("DB bootstrap completed", extra={"attempt": attempt})
        return


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.bootstrap_enforced = True
    engine = get_engine()
    bootstrap_task = asyncio.create_task(_bootstrap_db_until_ready(app))
    app.state.bootstrap_task = bootstrap_task

    yield

    # --- Graceful shutdown ---
    if not bootstrap_task.done():
        bootstrap_task.cancel()
        with suppress(asyncio.CancelledError):
            await bootstrap_task
    app.state.ready = False
    app.state.bootstrap_enforced = False
    engine.dispose()


app = FastAPI(
    title="OpenJobsEU Runtime",
    version="0.1.0",
    lifespan=lifespan,
)

configure_oauth(app)


app.add_middleware(
    SessionMiddleware,
    # WARNING: This default key is for development/testing purposes only.
    # In a production environment, you must set the SESSION_SECRET_KEY environment variable.
    secret_key=os.environ.get("SESSION_SECRET_KEY", "a-very-secret-key-for-dev"),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://openjobseu.org"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(jobs_router)


@app.middleware("http")
async def readiness_gate(request: Request, call_next):
    if request.url.path in READINESS_EXEMPT_PATHS:
        return await call_next(request)

    bootstrap_enforced = bool(getattr(app.state, "bootstrap_enforced", False))
    is_ready = bool(getattr(app.state, "ready", False))
    if bootstrap_enforced and not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "detail": "service_initializing"},
        )

    return await call_next(request)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready(response: Response):
    bootstrap_enforced = bool(getattr(app.state, "bootstrap_enforced", False))
    is_ready = bool(getattr(app.state, "ready", False))
    if not bootstrap_enforced:
        is_ready = True
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": is_ready}
