''' 
this file now acts as a facade re-exporting functions from the new repository modules,
while keeping its original public API.
'''

import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db_engine import get_engine
from app.domain.taxonomy.taxonomy import classify_taxonomy
from .common import _string_like, _derive_source_fields, _require_open_conn

engine = get_engine()
MIGRATIONS_PATH = Path("storage/migrations")
logger = logging.getLogger(__name__)

def init_db():
    db_engine = get_engine()

    with db_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL
            )
        """))

        applied_rows = conn.execute(text("SELECT version FROM schema_migrations"))
        applied_versions = {row[0] for row in applied_rows}

        migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))
        migration_versions = {int(file.name.split("_")[0]) for file in migration_files}

        if not applied_versions:
            existing_jobs = conn.execute(
                text("SELECT to_regclass('public.jobs')")
            ).scalar_one_or_none()
            existing_companies = conn.execute(
                text("SELECT to_regclass('public.companies')")
            ).scalar_one_or_none()

            if existing_jobs and existing_companies:
                # Legacy databases may already contain baseline tables but miss
                # the migration ledger. Mark only baseline schema as applied so
                # newer migrations still run.
                baseline_versions = {1, 2} & migration_versions
                now = datetime.now(timezone.utc)
                conn.execute(
                    text("""
                        INSERT INTO schema_migrations (version, applied_at)
                        VALUES (:version, :applied_at)
                        ON CONFLICT (version) DO NOTHING
                    """),
                    [
                        {"version": version, "applied_at": now}
                        for version in sorted(baseline_versions)
                    ],
                )
                applied_versions = set(baseline_versions)

        for migration_file in migration_files:
            version = int(migration_file.name.split("_")[0])
            if version in applied_versions:
                continue

            sql = migration_file.read_text()
            conn.execute(text(sql))
            conn.execute(
                text("""
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (:version, :applied_at)
                """),
                {"version": version, "applied_at": datetime.now(timezone.utc)},
            )


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
    _job_exists,
    _resolve_canonical_job_id,
    _upsert_job_source_mapping_in_conn,
    _upsert_job_in_conn,
    upsert_job,
    get_jobs,
)
from .repositories.compliance_repository import (
    insert_compliance_report,
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
