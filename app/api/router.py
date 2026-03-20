from fastapi import APIRouter

from app.api.audit import audit_ui_router, audit_api_router
from app.api.discovery import discovery_router
from app.api.tasks import tasks_router
from app.api.system import system_router

router = APIRouter(prefix="/internal")

router.include_router(audit_ui_router)
router.include_router(audit_api_router)
router.include_router(discovery_router)
router.include_router(tasks_router)
router.include_router(system_router)