from datetime import datetime, timezone
import logging
from sqlalchemy import text
from app.domain.classification.enums import RemoteClass, GeoClass
from app.domain.compliance.engine import apply_policy, ENGINE_POLICY_VERSION
from storage.db_engine import get_engine
from storage.db_logic import insert_compliance_report

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    engine = get_engine()

    logger.info("Starting compliance backfill...")

    # 1. Fetch jobs missing compliance data or with outdated policy
    query = text("""
        SELECT
            job_id, job_uid, title, description, remote_scope, source,
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

            job_input = {
                "title": job_data["title"] or "",
                "description": job_data["description"] or "",
                "remote_scope": job_data["remote_scope"] or "",
            }

            try:
                job_with_compliance, reason = apply_policy(job_input, source=job_data["source"] or "unknown")

                compliance_payload = job_with_compliance.get("_compliance", {})

                remote_class = compliance_payload.get("remote_model")
                geo_class = compliance_payload.get("geo_class")
                policy_version = compliance_payload.get("policy_version") or ENGINE_POLICY_VERSION.value

                remote_class_val = str(getattr(remote_class, "value", remote_class))
                geo_class_val = str(getattr(geo_class, "value", geo_class))
                policy_version_val = str(getattr(policy_version, "value", policy_version))
                compliance_status = compliance_payload.get("compliance_status")
                compliance_score = compliance_payload.get("compliance_score")
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

                    for entry in report_entries:
                        insert_compliance_report(
                            conn,
                            job_id=entry["job_id"],
                            job_uid=entry["job_uid"],
                            policy_version=entry["policy_version"],
                            remote_class=entry["remote_class"],
                            geo_class=entry["geo_class"],
                            hard_geo_flag=entry["hard_geo_flag"],
                            base_score=entry["base_score"],
                            final_score=entry["final_score"],
                            final_status=entry["final_status"],
                            decision_vector=entry["decision_vector"]
                        )

                updated += len(job_updates)
            except Exception as e:
                logger.error(f"Failed to update batch: {e}")

        processed += len(batch)
        logger.info(f"Progress: {processed}/{total_found} (updated: {updated})")

    logger.info(f"Backfill finished. Total jobs updated: {updated}")
    return updated