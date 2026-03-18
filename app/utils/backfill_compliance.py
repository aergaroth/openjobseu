from datetime import datetime, timezone
import logging
from sqlalchemy import text
from app.domain.taxonomy.enums import RemoteClass, GeoClass
from app.domain.compliance.engine import apply_policy, ENGINE_POLICY_VERSION
from storage.db_engine import get_engine
from storage.repositories.compliance_repository import insert_compliance_reports

logger = logging.getLogger("openjobseu.backfill")

BATCH_SIZE = 100

def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    engine = get_engine()

    logger.info("Starting compliance backfill...")

    # 1. Fetch jobs missing compliance data or with outdated policy
    query = text("""
        SELECT
            job_id, job_uid, title, description, remote_scope, source,
            company_id, company_name, remote_source_flag,
            remote_class, geo_class, compliance_status, compliance_score, policy_version
        FROM jobs
        WHERE compliance_status IS NULL
           OR compliance_score IS NULL
           OR policy_version IS NULL
           OR policy_version != :current_policy_version
        ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
        LIMIT :limit
    """)

    rows = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit, "current_policy_version": ENGINE_POLICY_VERSION.value}).mappings().all()

    total_found = len(rows)
    logger.info(f"Found {total_found} jobs to backfill")

    if total_found == 0:
        return 0

    processed = 0
    updated = 0

    for i in range(0, total_found, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        job_updates = []
        report_entries = []

        for row in batch:
            job_data = dict(row)
            job_id = job_data["job_id"]
            job_uid = job_data["job_uid"]

            job_input = dict(job_data)

            try:
                job_with_compliance, reason = apply_policy(job_input, source=job_data["source"] or "unknown")

                # Zabezpieczenie przed rzucaniem AttributeError dla odrzuconych ofert (None)
                compliance_payload = (job_with_compliance or job_input).get("_compliance", {})
                
                compliance_status = compliance_payload.get("compliance_status")
                compliance_score = compliance_payload.get("compliance_score")
                
                # Fallback zapobiegający zostaniu oferty ze statusem NULL (usunięcie "martwych dusz" z kolejki)
                if not compliance_status:
                    compliance_status = "review"
                    compliance_score = 0

                remote_class = compliance_payload.get("remote_model")
                geo_class = compliance_payload.get("geo_class")
                policy_version = compliance_payload.get("policy_version") or ENGINE_POLICY_VERSION.value

                # Prawidłowe unikanie tekstowych wartości "None" w bazie danych
                remote_class_val = remote_class.value if hasattr(remote_class, "value") else remote_class
                geo_class_val = geo_class.value if hasattr(geo_class, "value") else geo_class
                policy_version_val = policy_version.value if hasattr(policy_version, "value") else policy_version
                decision_trace = compliance_payload.get("decision_trace")

                job_updates.append({
                    "job_id": job_id,
                    "remote_class": remote_class_val,
                    "geo_class": geo_class_val,
                    "compliance_status": compliance_status,
                    "compliance_score": compliance_score,
                    "policy_version": policy_version_val,
                    "updated_at": datetime.now(timezone.utc)
                })

                report_entries.append({
                    "job_id": job_id,
                    "job_uid": job_uid,
                    "policy_version": policy_version_val,
                    "remote_class": remote_class_val,
                    "geo_class": geo_class_val,
                    "hard_geo_flag": bool(compliance_payload.get("policy_reason") == "geo_restriction_hard"),
                    "base_score": compliance_score,
                    "penalties": None,
                    "bonuses": None,
                    "final_score": compliance_score,
                    "final_status": compliance_status,
                    "decision_vector": decision_trace
                })

            except Exception as e:
                logger.error(f"Failed to process job {job_id}: {e}")
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE jobs
                            SET
                                remote_class = :remote_class,
                                geo_class = :geo_class,
                                compliance_status = :compliance_status,
                                compliance_score = :compliance_score,
                                policy_version = :policy_version,
                                updated_at = :updated_at
                            WHERE job_id = :job_id
                        """),
                        job_updates
                    )

                    if report_entries:
                        insert_compliance_reports(conn, report_entries)

                    updated += len(job_updates)
            except Exception as e:
                logger.error(f"Failed to update batch: {e}")

        processed += len(batch)
        pct = int((processed / total_found) * 100)
        filled = int(20 * processed / total_found)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(f"compliance_backfill progress: [{bar}] {pct}% ({processed}/{total_found}) | updated: {updated}")

    logger.info(f"Backfill finished. Total jobs updated: {updated}")
    return updated