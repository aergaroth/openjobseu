from typing import Tuple

from app.workers.policy.v1 import apply_policy_v1
from app.workers.policy.v2.remote_classifier import classify_remote_model
from app.workers.policy.v3.hard_geo_detector import detect_hard_geo_restriction


def apply_policy_v3(job: dict, source: str) -> Tuple[dict | None, str | None]:
    """
    V3 policy for employer ingestion only.

    1. Hard geo restriction detection (title + description + remote_scope + metadata)
    2. Immediate hard reject if detected
    3. Fallback to V1 logic otherwise
    """

    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    remote_scope = str(job.get("remote_scope") or "")
    source_field = str(job.get("source") or "")
    source_url = str(job.get("source_url") or "")
    remote_model = "unknown"

    try:
        remote_model = str(
            classify_remote_model(
                title=title,
                description=description,
                remote_scope=remote_scope,
            ).get("remote_model")
            or "unknown"
        )
    except Exception:
        remote_model = "unknown"

    combined_text = " ".join(
        [title, description, remote_scope, source_field, source_url]
    )

    # STEP 1 — Hard geo restriction
    if detect_hard_geo_restriction(combined_text):
        rejected_job = job.copy()
        rejected_job["compliance_status"] = "rejected"
        rejected_job["compliance_score"] = 0
        rejected_job["_compliance"] = {
            "policy_version": "v3",
            "policy_reason": "geo_restriction_hard",
            "remote_model": remote_model,
        }
        return rejected_job, "geo_restriction_hard"

    # STEP 2 — Fallback to existing logic
    job_after_v1, reason = apply_policy_v1(job, source=source)

    if job_after_v1 is None:
        return None, reason

    job_after_v1["_compliance"] = job_after_v1.get("_compliance", {})
    job_after_v1["_compliance"]["policy_version"] = "v3"

    return job_after_v1, reason
