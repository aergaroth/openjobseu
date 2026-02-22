import re
from typing import Dict

from app.workers.policy.v2.geo_data import (
    APAC_STRONG_SIGNALS,
    AUSTRALIA_STRONG_SIGNALS,
    CANADA_STRONG_SIGNALS,
    EU_MEMBER_STATES,
    EU_REGION_KEYWORDS,
    EOG_COUNTRIES,
    INDIA_STRONG_SIGNALS,
    LATAM_STRONG_SIGNALS,
    NON_EU_RESTRICTED,
    UK_KEYWORDS,
    US_STATE_CODES,
    US_STATE_SIGNAL_THRESHOLD,
    US_STRONG_SIGNALS,
)

US_STATE_CODES_RE = re.compile(
    r"\b(?:" + "|".join(code.upper() for code in US_STATE_CODES) + r")\b",
    re.IGNORECASE,
)


def _contains_phrase(full_text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", full_text) is not None


def _count_us_state_signal_hits(full_text: str) -> int:
    hits = {match.group(0).lower() for match in US_STATE_CODES_RE.finditer(full_text)}
    return len(hits)


def classify_geo_scope(title: str, description: str) -> Dict:
    """
    Deterministic geo classifier (v2).

    Pure function:
    - no DB
    - no scoring
    - no logging
    """

    full_text = f"{title or ''} {description or ''}".lower()

    # 1) Hard non-EU restrictions first
    for kw in US_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in CANADA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in APAC_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in AUSTRALIA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in INDIA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in LATAM_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    for kw in NON_EU_RESTRICTED:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "non_eu",
                "matched_keyword": kw,
            }

    # 2) US states by abbreviation (>=3) => non-EU
    us_state_hits = _count_us_state_signal_hits(full_text)
    if us_state_hits >= US_STATE_SIGNAL_THRESHOLD:
        return {
            "geo_class": "non_eu",
            "matched_keyword": f"us_state_codes>={US_STATE_SIGNAL_THRESHOLD}",
        }

    # 3) Explicit EU mention
    if (
        _contains_phrase(full_text, "eu only")
        or _contains_phrase(full_text, "eu-only")
        or _contains_phrase(full_text, "european union")
    ):
        return {
            "geo_class": "eu_explicit",
            "matched_keyword": "eu",
        }

    # 4) EU member states
    for country in EU_MEMBER_STATES:
        if _contains_phrase(full_text, country):
            return {
                "geo_class": "eu_member_state",
                "matched_keyword": country,
            }

    # 5) EOG / EEA region
    for country in EOG_COUNTRIES:
        if _contains_phrase(full_text, country):
            return {
                "geo_class": "eu_region",
                "matched_keyword": country,
            }
    for kw in EU_REGION_KEYWORDS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "eu_region",
                "matched_keyword": kw,
            }

    # 6) UK
    for kw in UK_KEYWORDS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": "uk",
                "matched_keyword": kw,
            }
    if re.search(r"\buk\b", full_text):
        return {
            "geo_class": "uk",
            "matched_keyword": "uk",
        }

    # 7) Fallback
    return {
        "geo_class": "unknown",
        "matched_keyword": None,
    }
