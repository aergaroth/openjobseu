from fastapi import APIRouter, Depends

from app.security.auth import (
    require_user_login,
    require_user_api_access,
    require_internal_or_user_api_access,
)
from app.security.internal_access import require_internal_access

from app.api.audit import audit_ui_router, audit_api_router
from app.api.discovery import discovery_ui_router, discovery_ops_router
from app.api.tasks import tasks_router
from app.api.system import system_ops_router, system_hybrid_router

router = APIRouter(prefix="/internal")

# 1. Frontend Admin Panel (HTML Views) - Wymaga poprawnej sesji w przeglądarce
admin_ui = APIRouter(dependencies=[Depends(require_user_login)])
admin_ui.include_router(audit_ui_router)

# 2. Frontend Admin Panel (API calls) - Wymaga poprawnej sesji, zwraca czysty JSON
admin_api = APIRouter(dependencies=[Depends(require_user_api_access)])
admin_api.include_router(audit_api_router)
admin_api.include_router(discovery_ui_router)

# 3. Backend Operations (Machine-to-Machine) - Wymaga weryfikacji tokenem OIDC (Scheduler/Gcloud)
ops_api = APIRouter(dependencies=[Depends(require_internal_access)])
ops_api.include_router(system_ops_router)
ops_api.include_router(discovery_ops_router)

# 4. Hybrid API - Używane zarówno przez Admin Panel jak i maszyny operacyjne
hybrid_api = APIRouter(dependencies=[Depends(require_internal_or_user_api_access)])
hybrid_api.include_router(system_hybrid_router)
hybrid_api.include_router(tasks_router)

router.include_router(admin_ui)
router.include_router(admin_api)
router.include_router(ops_api)
router.include_router(hybrid_api)
