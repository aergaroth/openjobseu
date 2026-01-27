from fastapi import FastAPI
from datetime import datetime, timezone

from app.internal import router as internal_router

app = FastAPI(title="OpenJobsEU Runtime", version="0.1.0")

app.include_router(internal_router)


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
