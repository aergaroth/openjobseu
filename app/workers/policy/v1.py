from typing import Dict


NON_REMOTE_KEYWORDS = [
    "onsite",
    "on-site",
    "in office",
    "in-office",
    "hybrid",
    "relocation required",
    "must be located in",
]

GEO_RESTRICT_KEYWORDS = [
    "us only",
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


def evaluate_policy(job: Dict) -> bool:
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
        return False

    # Geo restriction check
    if contains_any(full_text, GEO_RESTRICT_KEYWORDS):
        return False

    return True
