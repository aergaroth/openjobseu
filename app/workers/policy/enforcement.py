import logging
from typing import Dict, Optional, Tuple

from app.workers.policy.v1 import evaluate_policy

audit_logger = logging.getLogger("openjobseu.policy.audit")


def apply_policy_v1(job: Optional[Dict], *, source: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Apply policy v1 on a normalized job.

    This runs after normalization and before persistence.
    """
    if not job:
        return None, None

    # Kept for API compatibility with ingestion callers.
    _ = source

    accepted, reason = evaluate_policy(job)
    if not accepted:
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
