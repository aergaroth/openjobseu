import logging
from typing import Dict, Optional, Tuple

from app.workers.policy.v1 import evaluate_policy
from app.workers.policy.v2.remote_classifier import classify_remote_model

audit_logger = logging.getLogger("openjobseu.policy.audit")


def apply_policy_v1(job: Optional[Dict], *, source: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Apply policy v1 on a normalized job.

    This runs after normalization and before persistence.
    """
    if job is None:
        return None, None

    # Kept for API compatibility with ingestion callers.
    _ = source

    decision, reason = evaluate_policy(job)

    try:
        classification = classify_remote_model(
            str(job.get("title") or ""),
            str(job.get("description") or ""),
        )
        remote_model = classification.get("remote_model")
    except Exception:
        remote_model = "unknown"

    job["_compliance"] = {
        "policy_version": "v1",
        "policy_reason": reason,
        "remote_model": remote_model,
    }

    if not decision:
        audit_logger.info(
            f"policy_reject[{source}]",
            extra={
                "component": "policy",
                "job_id": job.get("job_id"),
                "reason": reason,
                "policy_version": "v1",
            },
        )
        return None, reason

    return job, None
