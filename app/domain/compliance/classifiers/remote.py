from app.domain.taxonomy.enums import RemoteClass

V2_NEGATIVE_STRONG = [
    "relocation required",
    "on-site",
    "onsite",
    "in-office",
    "in office",
    "office based",
    "office-based",
    "this role is based in",
    "full-time position in",
]

V2_HYBRID_SIGNALS = [
    "hybrid",
    "days in office",
    "days a week in the office",
    "partially remote",
    "partly remote",
]

V2_REMOTE_STRONG = [
    "fully remote",
    "100% remote",
    "remote only",
    "remote-only",
    "remote-first",
    "remote first",
    "work from anywhere",
    "work where you work best",
    "home based",
    "remote job",
    "work from home",
]

V2_REMOTE_OPTIONAL_SIGNALS = [
    "remote work options",
    "flexible remote",
    "possibility to work remotely",
    "flexible working hours and remote",
    "remote friendly",
    "remote-friendly",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def is_region_locked(remote_scope: str | None) -> bool:
    if not remote_scope:
        return False

    text = remote_scope.lower()

    if "remote" not in text:
        return False

    cleaned = text.replace("remote", "").replace(",", "").strip()
    return len(cleaned) > 0


def classify_remote(
    *,
    title: str,
    description: str,
    remote_scope: str,
) -> dict:
    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    scope_l = (remote_scope or "").lower()

    # 1 Scope has explicit office/hybrid signals
    if any(k in scope_l for k in V2_NEGATIVE_STRONG) or any(k in scope_l for k in V2_HYBRID_SIGNALS):
        return {
            "remote_model": RemoteClass.NON_REMOTE,
            "reason": "scope_negative_or_hybrid",
        }

    # 2 Scope contains strong remote signal
    found_keyword = next((k for k in V2_REMOTE_STRONG if k in scope_l), None)
    if not found_keyword and "remote" in scope_l:
        found_keyword = "remote"

    if found_keyword:
        cleaned = scope_l.replace(found_keyword, "").replace("-", "").replace(",", "").strip()
        if cleaned and cleaned not in ("yes", "true", "1", "anywhere", "worldwide"):
            return {
                "remote_model": RemoteClass.REMOTE_REGION_LOCKED,
                "reason": "scope_region",
            }
        return {
            "remote_model": RemoteClass.REMOTE_ONLY,
            "reason": f"scope_{found_keyword.replace(' ', '_')}",
        }

    # 3 Title contains remote
    if "remote" in title_l:
        return {"remote_model": RemoteClass.REMOTE_ONLY, "reason": "title_remote"}

    # 4 Hybrid detection (strong negative)
    if any(k in desc_l for k in V2_HYBRID_SIGNALS):
        return {"remote_model": RemoteClass.NON_REMOTE, "reason": "hybrid_signal"}

    # 5 Strong Remote in description (This was previously missing!)
    if any(k in desc_l for k in V2_REMOTE_STRONG):
        return {"remote_model": RemoteClass.REMOTE_ONLY, "reason": "desc_remote_strong"}

    # 6 Explicit negative in description
    if any(k in desc_l for k in V2_NEGATIVE_STRONG):
        return {"remote_model": RemoteClass.NON_REMOTE, "reason": "desc_negative"}

    # 7 Optional remote (benefit)
    if any(k in desc_l for k in V2_REMOTE_OPTIONAL_SIGNALS):
        return {"remote_model": RemoteClass.REMOTE_OPTIONAL, "reason": "benefit_remote"}

    return {"remote_model": RemoteClass.UNKNOWN, "reason": "no_signal"}


def classify_remote_v3(*, title: str, description: str, remote_scope: str) -> dict:
    return classify_remote(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )


def classify_remote_model(title: str, description: str, remote_scope: str = "") -> dict:
    title = (title or "").lower()
    description = (description or "").lower()
    remote_scope = (remote_scope or "").lower()
    text = f"{title} {description} {remote_scope}"

    # 1 Office first
    if _contains_any(text, V2_NEGATIVE_STRONG):
        return {
            "remote_model": "office_first",
            "confidence": 0.95,
            "signals": ["negative_strong"],
        }

    # 2 Hybrid
    if _contains_any(text, V2_HYBRID_SIGNALS):
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
    if _contains_any(text, V2_REMOTE_STRONG):
        return {
            "remote_model": RemoteClass.REMOTE_ONLY.value,
            "confidence": 0.9,
            "signals": ["remote_strong"],
        }

    # 5 Optional remote (benefit, not model)
    if _contains_any(text, V2_REMOTE_OPTIONAL_SIGNALS):
        return {
            "remote_model": RemoteClass.REMOTE_OPTIONAL.value,
            "confidence": 0.7,
            "signals": [RemoteClass.REMOTE_OPTIONAL.value],
        }

    return {
        "remote_model": RemoteClass.UNKNOWN.value,
        "confidence": 0.3,
        "signals": [],
    }
