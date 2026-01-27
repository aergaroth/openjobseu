from fastapi import APIRouter

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/tick")
def tick():
    return {
        "status": "ok",
        "message": "scheduler tick received"
    }
