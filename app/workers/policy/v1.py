from typing import Dict, Optional, Tuple

from app.workers.policy.v2.remote_classifier import classify_remote_model


NON_REMOTE_KEYWORDS = [
    "onsite",
    "on-site",
    "in office",
    "in-office",
    "hybrid",
    "relocation required"
]

GEO_RESTRICT_KEYWORDS = [
    "us only",
    "usa only",
    "united states only",
    "us citizens",
    "us work authorization",
    "must be based in the us",
    "must be based in us",
    "north america only",
    "canada only",
    "apac only",
]


def contains_any(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(k in text for k in keywords)


def evaluate_policy(job: Dict) -> Tuple[bool, Optional[str]]:
    """
    Policy v1:
    - Reject non-remote roles
    - Reject geo-restricted (non EU-friendly) roles
    """

    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()

    full_text = f"{title} {description}"

    # Remote purity check
    if contains_any(full_text, NON_REMOTE_KEYWORDS):
        return False, "non_remote"

    # Geo restriction check
    if contains_any(full_text, GEO_RESTRICT_KEYWORDS):
        return False, "geo_restriction"

    return True, None

def apply_policy_v1(job: Optional[Dict], *, source: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Apply policy v1 and annotate compliance metadata.

    This function does not hard-reject jobs.
    It returns policy reason as a soft signal.
    """
    if job is None:
        return None, None

    decision, reason = evaluate_policy(job)

    try:
        classification = classify_remote_model(
            title=str(job.get("title") or ""),
            description=str(job.get("description") or ""),
            remote_scope=str(job.get("remote_scope") or ""),
        )
        remote_model = classification.get("remote_model")
    except Exception:
        remote_model = "unknown"

    job["_compliance"] = {
        "policy_version": "v1",
        "policy_reason": reason,
        "remote_model": remote_model,
    }

    return job, reason
