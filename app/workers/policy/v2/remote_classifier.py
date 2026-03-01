from typing import Dict, List


NEGATIVE_STRONG = [
    "relocation required",
    "on-site",
    "onsite",
    "in-office",
    "in office",
    "this role is based in",
    "full-time position in",
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

REMOTE_OPTIONAL_SIGNALS = [
    "remote work options",
    "flexible remote",
    "possibility to work remotely",
    "flexible working hours and remote",
]

def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(k in text for k in keywords)

def is_region_locked(remote_scope: str | None) -> bool:
    if not remote_scope:
        return False

    text = remote_scope.lower()

    if "remote" not in text:
        return False

    cleaned = text.replace("remote", "").replace(",", "").strip()

    return len(cleaned) > 0


def classify_remote_model(title: str, description: str, remote_scope: str = "") -> Dict:
    title = (title or "").lower()
    description = (description or "").lower()
    remote_scope = (remote_scope or "").lower()
    text = f"{title} {description} {remote_scope}"
    

    # 1 Office first
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
            "confidence": 0.85,
            "signals": ["hybrid_signal"],
        }

    # 3 Region-locked remote based on remote_scope
    if is_region_locked(remote_scope):
        return {
            "remote_model": "remote_but_geo_restricted",
            "confidence": 0.8,
            "signals": ["remote_scope_region_locked"],
        }

    # 4 Fully remote
    if _contains_any(text, REMOTE_STRONG):
        return {
            "remote_model": "remote_only",
            "confidence": 0.9,
            "signals": ["remote_strong"],
        }

    # 5 Optional remote (benefit, not model)
    if _contains_any(text, REMOTE_OPTIONAL_SIGNALS):
        return {
            "remote_model": "remote_optional",
            "confidence": 0.7,
            "signals": ["remote_optional"],
        }

    return {
        "remote_model": "unknown",
        "confidence": 0.3,
        "signals": [],
    }
