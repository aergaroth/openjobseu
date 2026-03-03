import re
from typing import Dict

from app.domain.classification.enums import GeoClass
from app.workers.policy.v3.geo_data_v3 import (
    EU_MEMBER_STATES,
    UK_KEYWORDS,
    EU_REGION_CUSTOM,
    NON_EU_REGION_CUSTOM,
    COUNTRY_ALIASES,
#    REGION_KEYWORDS
)


def _normalize_token(tok: str) -> str:
    return tok.strip().lower().strip("()").rstrip(".")


def classify_geo_v3(
    *,
    title: str,
    description: str,
    remote_scope: str,
) -> Dict:

    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    scope_l = (remote_scope or "").lower()

    full_text = f"{title_l} {desc_l} {scope_l}"

    # ------------------------------------------------------------
    # 1 HARD NON-EU REGIONS (najwyższy priorytet)
    # ------------------------------------------------------------
    for kw in NON_EU_REGION_CUSTOM:
        if kw in full_text:
            return {"geo_class": GeoClass.NON_EU, "reason": kw}

    # ------------------------------------------------------------
    # 2 EU REGION CUSTOM (EMEA, Nordics, Western Europe, UK&I)
    # ------------------------------------------------------------
    for kw in EU_REGION_CUSTOM:
        if kw in full_text:
            return {"geo_class": GeoClass.EU_REGION, "reason": kw}

    # ------------------------------------------------------------
    # 3 Structured parsing of remote_scope (najbardziej wiarygodne)
    # ------------------------------------------------------------
    if scope_l:
        parts = re.split(r"[;,/]+", scope_l)
        tokens = [_normalize_token(p) for p in parts if p.strip()]

        found_eu = False
        found_non_eu = False

        for t in tokens:
            # alias (if using COUNTRY_ALIASES)
            if t in COUNTRY_ALIASES:
                mapped_full_name = COUNTRY_ALIASES[t].lower()
                if mapped_full_name in EU_MEMBER_STATES:
                    found_eu = True
                else:
                    found_non_eu = True
                continue

            # pełna nazwa kraju
            if t in EU_MEMBER_STATES:
                found_eu = True
                continue

            # UK osobno
            if t in UK_KEYWORDS:
                found_eu = True
                continue

        if found_eu and found_non_eu:
            return {"geo_class": GeoClass.EU_REGION, "reason": "mixed_region"}

        if found_eu:
            return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": "explicit_country"}

        if found_non_eu:
            return {"geo_class": GeoClass.NON_EU, "reason": "explicit_country"}

    # ------------------------------------------------------------
    # 4 EU member states in whole text (fallback)
    # ------------------------------------------------------------
    for country in EU_MEMBER_STATES:
        if country in full_text:
            return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": country}

    # ------------------------------------------------------------
    # 5 UK (fallback)
    # ------------------------------------------------------------
    for kw in UK_KEYWORDS:
        if kw in full_text:
            return {"geo_class": GeoClass.UK, "reason": kw}

    # ------------------------------------------------------------
    # 6 Unknown
    # ------------------------------------------------------------
    return {"geo_class": GeoClass.UNKNOWN, "reason": None}
