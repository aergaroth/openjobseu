from typing import Dict, Optional, Tuple

from app.workers.policy.v1 import evaluate_policy


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
        return None, reason

    return job, None
