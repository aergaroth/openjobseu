from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(title="OpenJobsEU Runtime", version="0.1.0")


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
