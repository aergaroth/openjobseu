import logging
from typing import Dict, Optional

from app.workers.policy.v1 import evaluate_policy


logger = logging.getLogger("openjobseu.policy")


def apply_policy_v1(job: Optional[Dict], *, source: str) -> Optional[Dict]:
    """
    Apply policy v1 on a normalized job.

    This runs after normalization and before persistence.
    """
    if not job:
        return None

    if not evaluate_policy(job):
        logger.info(
            "job rejected by policy",
            extra={
                "source": source,
                "policy_version": "v1",
                "job_id": job.get("job_id"),
            },
        )
        return None

    return job
