from typing import Dict

from app.domain.classification.enums import RemoteClass


REMOTE_WORD = "remote"

REMOTE_OPTIONAL_SIGNALS = [
    "remote work options",
    "flexible remote",
    "home office",
    "workation",
]

HYBRID_SIGNALS = [
    "hybrid",
    "days in office",
]

NEGATIVE_STRONG = [
    "relocation required",
    "full-time position in",
    "this role is based in",
]


def classify_remote_v3(
    *,
    title: str,
    description: str,
    remote_scope: str,
) -> Dict:

    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    scope_l = (remote_scope or "").lower()

    # 1 Scope has explicit office signals
    if any(k in scope_l for k in NEGATIVE_STRONG):
        return {"remote_model": RemoteClass.NON_REMOTE, "reason": "scope_negative"}

    # 2 Scope contains "remote"
    if REMOTE_WORD in scope_l:
        cleaned = scope_l.replace("remote", "").replace("-", "").strip()
        if cleaned:
            return {
                "remote_model": RemoteClass.REMOTE_REGION_LOCKED,
                "reason": "scope_region",
            }
        return {"remote_model": RemoteClass.REMOTE_ONLY, "reason": "scope_remote"}

    # 3 Title contains remote
    if REMOTE_WORD in title_l:
        return {"remote_model": RemoteClass.REMOTE_ONLY, "reason": "title_remote"}

    # 4 Hybrid detection (strong negative)
    if any(k in desc_l for k in HYBRID_SIGNALS):
        return {"remote_model": RemoteClass.NON_REMOTE, "reason": "hybrid_signal"}

    # 5 Optional remote (benefit)
    if any(k in desc_l for k in REMOTE_OPTIONAL_SIGNALS):
        return {"remote_model": RemoteClass.REMOTE_OPTIONAL, "reason": "benefit_remote"}

    return {"remote_model": RemoteClass.UNKNOWN, "reason": "no_signal"}
