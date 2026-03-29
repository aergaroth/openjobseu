from datetime import datetime, timezone
import logging
from app.domain.compliance.engine import apply_policy, ENGINE_POLICY_VERSION
from storage.db_engine import get_engine
from storage.repositories.compliance_repository import (
    get_jobs_for_compliance_backfill,
    insert_compliance_reports,
    update_job_compliance_data,
)

logger = logging.getLogger("openjobseu.backfill")

BATCH_SIZE = 100


def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    engine = get_engine()

    logger.info("Starting compliance backfill...")

    rows = []
    # FIX 1: Wrap initial data fetch in a transaction for consistency
    with engine.begin() as conn:
        rows = get_jobs_for_compliance_backfill(conn, limit=limit, current_policy_version=ENGINE_POLICY_VERSION.value)

    total_found = len(rows)
    logger.info(f"Found {total_found} jobs to backfill")

    if total_found == 0:
        return 0

    processed = 0
    updated = 0

    for i in range(0, total_found, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        job_updates = []
        report_entries = []

        for row in batch:
            job_data = dict(row)
            job_id = job_data["job_id"]
            job_uid = job_data["job_uid"]

            # FIX 2: Use explicit mapping for data passed to apply_policy
            job_input = {
                "title": job_data["title"],
                "description": job_data["description"],
                "company_name": job_data["company_name"],
                "remote_scope": job_data["remote_scope"],
                "remote_source_flag": job_data["remote_source_flag"],
                "remote_class": job_data["remote_class"],
                "geo_class": job_data["geo_class"],
            }

            try:
                job_with_compliance, reason = apply_policy(job_input, source=job_data["source"] or "unknown")

                # FIX 3: Correct misleading comment
                # Safely get compliance payload, falling back to an empty dict if the job was rejected.
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

                job_updates.append(
                    {
                        "job_id": job_id,
                        "remote_class": remote_class_val,
                        "geo_class": geo_class_val,
                        "compliance_status": compliance_status,
                        "compliance_score": compliance_score,
                        "policy_version": policy_version_val,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )

                # FIX 4: Map penalties/bonuses from compliance payload if available
                report_entries.append(
                    {
                        "job_id": job_id,
                        "job_uid": job_uid,
                        "policy_version": policy_version_val,
                        "remote_class": remote_class_val,
                        "geo_class": geo_class_val,
                        "hard_geo_flag": bool(compliance_payload.get("policy_reason") == "geo_restriction_hard"),
                        "base_score": compliance_score,
                        "penalties": compliance_payload.get("penalties"),
                        "bonuses": compliance_payload.get("bonuses"),
                        "final_score": compliance_score,
                        "final_status": compliance_status,
                        "decision_vector": decision_trace,
                    }
                )

            except Exception:
                # FIX 6: Use exc_info=True for proper traceback logging
                logger.error("Failed to process job %s", job_id, exc_info=True)
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    update_job_compliance_data(conn, job_updates)

                    if report_entries:
                        insert_compliance_reports(conn, report_entries)

                    updated += len(job_updates)
            except Exception:
                # FIX 5 & 6: Log failed IDs and use exc_info
                failed_ids = [j["job_id"] for j in job_updates]
                logger.warning("Failed to update batch. Job IDs: %s", failed_ids)
                logger.error("Batch update failed", exc_info=True)

        processed += len(batch)
        pct = int((processed / total_found) * 100)
        filled = int(20 * processed / total_found)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(f"compliance_backfill progress: [{bar}] {pct}% ({processed}/{total_found}) | updated: {updated}")

    logger.info(f"Backfill finished. Total jobs updated: {updated}")
    return updated
