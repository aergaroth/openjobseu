''' 
this file now acts as a facade re-exporting functions from the new repository modules,
while keeping its original public API.
'''

import logging
from storage.db_engine import get_engine
from app.domain.taxonomy.taxonomy import classify_taxonomy

engine = get_engine()
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Public storage facade
# -------------------------------------------------------------------


def _derive_taxonomy(job: dict) -> dict[str, str]:
    """Internal helper to derive taxonomy fields from a job dict."""
    title = (job.get("title") or "").strip()
    return classify_taxonomy(title)

def compute_job_taxonomy(job: dict) -> dict[str, str]:
    """Helper to derive taxonomy fields from a job dict for backward compatibility in tests."""
    return _derive_taxonomy(job)

# Re-exports for public API stability
from .repositories.jobs_repository import (
    _find_job_id_by_source_mapping,
    _find_job_id_by_fingerprint,
    _resolve_canonical_job_id,
    _upsert_job_source_mapping_in_conn,
    _upsert_job_in_conn,
    upsert_job,
    get_jobs,
)
from .repositories.compliance_repository import (
    insert_compliance_report,
    insert_compliance_reports,
    count_jobs_missing_compliance,
    get_jobs_for_compliance_resolution,
    update_job_compliance_resolution,
    update_jobs_compliance_resolution,
)
from .repositories.lifecycle_repository import (
    expire_jobs_due_to_lifecycle,
    stale_active_jobs_due_to_lifecycle,
    activate_new_jobs_due_to_lifecycle,
    reactivate_stale_jobs_due_to_lifecycle,
    mark_reposts_due_to_lifecycle,
)
from .repositories.availability_repository import (
    get_jobs_for_verification,
    update_job_availability,
    update_jobs_availability,
)
from .repositories.ats_repository import (
    load_active_ats_companies,
    mark_ats_synced,
    get_ats_integration_by_id,
    deactivate_ats_integration,
)
from .repositories.audit_repository import (
    _build_jobs_audit_filter_clauses,
    _rows_to_count_map,
    get_jobs_audit,
    get_compliance_stats_last_7d,
    get_audit_source_filter_values,
    get_audit_company_compliance_stats,
    get_audit_source_compliance_stats_last_7d,
    get_ghost_jobs,
    get_job_lifetime_stats,
    get_repost_candidates,
    get_failing_ats_integrations,
)
from .repositories.snapshots_repository import (
    insert_job_snapshot,
)
from .repositories.salary_repository import (
    insert_salary_parsing_case,
    insert_salary_parsing_cases,
)
