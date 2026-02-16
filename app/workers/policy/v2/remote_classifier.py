from typing import Dict, List


NEGATIVE_STRONG = [
    "we do not offer remote-only roles",
    "office-first company",
    "this role is based in",
    "based in our",
    "in-person collaboration",
    "relocation required",
]

HYBRID_SIGNALS = [
    "hybrid",
    "days in office",
    "partially remote",
]

REMOTE_STRONG = [
    "fully remote",
    "100% remote",
    "remote only",
    "remote-only",
    "remote-first",
    "work from anywhere",
]

GEO_RESTRICT_REMOTE = [
    "must be based in",
    "must be located in",
    "usa only",
    "united states only",
]


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(k in text for k in keywords)


def classify_remote_model(title: str, description: str) -> Dict:
    """
    Deterministic remote model classifier (Policy v2 - stage 1).

    Does NOT enforce rejection.
    Only classifies work model.
    """

    title = (title or "").lower()
    description = (description or "").lower()
    text = f"{title} {description}"

    # 1Hard negative first
    if _contains_any(text, NEGATIVE_STRONG):
        return {
            "remote_model": "office_first",
            "confidence": 0.95,
            "signals": ["negative_strong"],
        }

    # 2 Hybrid
    if _contains_any(text, HYBRID_SIGNALS):
        return {
            "remote_model": "hybrid",
            "confidence": 0.8,
            "signals": ["hybrid_signal"],
        }

    # 3 Remote but geo restricted
    if _contains_any(text, REMOTE_STRONG) and _contains_any(text, GEO_RESTRICT_REMOTE):
        return {
            "remote_model": "remote_but_geo_restricted",
            "confidence": 0.85,
            "signals": ["remote_strong", "geo_restrict"],
        }

    # 4 Strong remote
    if _contains_any(text, REMOTE_STRONG):
        return {
            "remote_model": "remote_only",
            "confidence": 0.9,
            "signals": ["remote_strong"],
        }

    return {
        "remote_model": "unknown",
        "confidence": 0.3,
        "signals": [],
    }
