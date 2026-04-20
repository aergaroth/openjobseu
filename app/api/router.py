from fastapi import APIRouter, Depends

from app.security.auth import (
    require_internal_or_user_ui_access,
    require_internal_or_user_api_access,
)
from app.security.internal_access import require_internal_access
from app.security.api_key import require_api_key

from app.api.audit import audit_ui_router, audit_api_router
from app.api.discovery import discovery_ui_router, discovery_ops_router
from app.api.tasks import tasks_trigger_router, tasks_execute_router
from app.api.system import system_ops_router, system_hybrid_router
from app.api.v1.key_management import key_mgmt_router
from app.api.v1.jobs import router as v1_jobs_router
from app.api.v1.analytics import router as v1_analytics_router

router = APIRouter(prefix="/internal")

# 1. Frontend Admin Panel (HTML Views) - Sesja użytkownika lub wewnętrzny proxy/bastion
admin_ui = APIRouter(dependencies=[Depends(require_internal_or_user_ui_access)])
admin_ui.include_router(audit_ui_router)

# 2. Frontend Admin Panel (API calls) - Sesja użytkownika lub wewnętrzny proxy/bastion
admin_api = APIRouter(dependencies=[Depends(require_internal_or_user_api_access)])
admin_api.include_router(audit_api_router)
admin_api.include_router(discovery_ui_router)
admin_api.include_router(key_mgmt_router)

# 3. Backend Operations (Machine-to-Machine) - Wymaga weryfikacji tokenem OIDC (Scheduler/Gcloud)
ops_api = APIRouter(dependencies=[Depends(require_internal_access)])
ops_api.include_router(system_ops_router)
ops_api.include_router(discovery_ops_router)
ops_api.include_router(tasks_execute_router)

# 4. Hybrid API - Używane zarówno przez Admin Panel jak i maszyny operacyjne
hybrid_api = APIRouter(dependencies=[Depends(require_internal_or_user_api_access)])
hybrid_api.include_router(system_hybrid_router)
hybrid_api.include_router(tasks_trigger_router)

router.include_router(admin_ui)
router.include_router(admin_api)
router.include_router(ops_api)
router.include_router(hybrid_api)

# 5. Paid Public API - Wymaga klucza API (Bearer ojeu_...)
paid_api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
paid_api_router.include_router(v1_jobs_router)
paid_api_router.include_router(v1_analytics_router)
