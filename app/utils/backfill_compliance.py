from datetime import datetime, timezone

import logging

from app.domain.compliance.engine import apply_policy, ENGINE_POLICY_VERSION
from storage.db_engine import get_engine
from storage.repositories.compliance_repository import (
    get_jobs_for_compliance_backfill,
    update_job_compliance_data,
    insert_compliance_reports,
)

logger = logging.getLogger("openjobseu.backfill")

# Records fetched, processed, and committed in one atomic unit.
# Small enough to keep memory pressure low; large enough to amortise DB round-trip cost.
CHUNK_SIZE = 100


def backfill_missing_compliance_classes(limit: int = 1000) -> int:
    """
    Re-evaluate compliance for jobs whose policy_version is stale or missing.

    Processes records in chunks of CHUNK_SIZE: each iteration fetches a fresh
    batch from the DB, runs apply_policy, and commits — no large in-memory list.

    Returns the total number of records *fetched and processed* (not just updated).
    Callers use this to detect whether the limit was hit (result == limit → more
    records likely remain → enqueue a continuation task).
    """
    engine = get_engine()

    logger.info("Starting compliance backfill (limit=%d, chunk_size=%d)", limit, CHUNK_SIZE)

    total_processed = 0
    total_updated = 0

    while total_processed < limit:
        chunk_size = min(CHUNK_SIZE, limit - total_processed)

        # Fresh fetch per chunk — avoids stale in-memory state and keeps RAM low.
        with engine.connect() as conn:
            rows = get_jobs_for_compliance_backfill(
                conn,
                limit=chunk_size,
                current_policy_version=ENGINE_POLICY_VERSION.value,
            )

        if not rows:
            break

        job_updates = []
        report_entries = []

        for row in rows:
            job_data = dict(row)
            job_id = job_data["job_id"]
            job_uid = job_data["job_uid"]

            try:
                job_with_compliance, reason = apply_policy(job_data, source=job_data["source"] or "unknown")

                compliance_payload = (job_with_compliance or job_data).get("_compliance", {})
                compliance_status = compliance_payload.get("compliance_status")
                compliance_score = compliance_payload.get("compliance_score")

                # Fallback zapobiegający zostaniu oferty ze statusem NULL
                if not compliance_status:
                    compliance_status = "review"
                    compliance_score = 0

                remote_class = compliance_payload.get("remote_model")
                geo_class = compliance_payload.get("geo_class")
                policy_version = compliance_payload.get("policy_version") or ENGINE_POLICY_VERSION.value
                decision_trace = compliance_payload.get("decision_trace")

                # Prawidłowe unikanie tekstowych wartości "None" w bazie danych
                remote_class_val = remote_class.value if hasattr(remote_class, "value") else remote_class
                geo_class_val = geo_class.value if hasattr(geo_class, "value") else geo_class
                policy_version_val = policy_version.value if hasattr(policy_version, "value") else policy_version

                # Wyciągnij penalties/bonuses z decision_trace zamiast hardkodować None
                scoring_step = next(
                    (s for s in (decision_trace or []) if s.get("step") == "scoring"),
                    {},
                )
                penalties = scoring_step.get("penalties") or None
                bonuses = scoring_step.get("bonuses") or None

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

                report_entries.append(
                    {
                        "job_id": job_id,
                        "job_uid": job_uid,
                        "policy_version": policy_version_val,
                        "remote_class": remote_class_val,
                        "geo_class": geo_class_val,
                        "hard_geo_flag": bool(compliance_payload.get("policy_reason") == "geo_restriction_hard"),
                        "base_score": compliance_score,
                        "penalties": penalties,
                        "bonuses": bonuses,
                        "final_score": compliance_score,
                        "final_status": compliance_status,
                        "decision_vector": decision_trace,
                    }
                )

            except Exception:
                logger.error("Failed to process job %s", job_id, exc_info=True)
                continue

        if job_updates:
            try:
                with engine.begin() as conn:
                    update_job_compliance_data(conn, job_updates)
                    if report_entries:
                        insert_compliance_reports(conn, report_entries)
                total_updated += len(job_updates)
            except Exception:
                logger.error(
                    "Failed to commit compliance chunk (first job_id=%s)", job_updates[0]["job_id"], exc_info=True
                )

        fetched = len(rows)
        total_processed += fetched

        filled = int(20 * total_processed / limit)
        bar = "█" * filled + "-" * (20 - filled)
        logger.info(
            "compliance_backfill progress: [%s] %d%% (%d/%d) | updated: %d",
            bar,
            int(total_processed / limit * 100),
            total_processed,
            limit,
            total_updated,
        )

        if fetched < chunk_size:
            break  # No more records available — done early

    logger.info("Compliance backfill finished. processed=%d updated=%d", total_processed, total_updated)
    return total_processed
