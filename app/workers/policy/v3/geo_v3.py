import re
from html import unescape
from typing import Dict

from app.domain.classification.enums import GeoClass
from app.workers.policy.v3.geo_data_v3 import (
    EU_MEMBER_STATES,
    UK_KEYWORDS,
    EU_REGION_CUSTOM,
    NON_EU_REGION_CUSTOM,
    COUNTRY_ALIASES,
    # REGION_KEYWORDS
)

HTML_LOCALIZATION_SECTION_RE = re.compile(
    r"(?is)<h[1-6][^>]*>\s*locali[sz]ation\s*:?\s*</h[1-6]>\s*(?P<section>.*?)(?=<h[1-6][^>]*>|$)"
)
HTML_TAG_RE = re.compile(r"(?is)<[^>]+>")
LOCALIZATION_INLINE_RE = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?locali[sz]ation\s*:\s*(?P<section>.+)$")
LOCALIZATION_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s*)?locali[sz]ation\s*:?\s*$", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
COLON_HEADING_RE = re.compile(r"^\s*[A-Za-z][A-Za-z0-9 /&()+-]{1,60}\s*:\s*$")


def _normalize_token(tok: str) -> str:
    return tok.strip().lower().strip("()").rstrip(".")


def _contains_phrase(full_text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", full_text) is not None


def _extract_localization_section(description: str) -> str:
    if not description:
        return ""

    html_match = HTML_LOCALIZATION_SECTION_RE.search(description)
    if html_match:
        section_html = html_match.group("section")
        section_text = HTML_TAG_RE.sub(" ", section_html)
        return " ".join(unescape(section_text).split()).lower()

    inline_match = LOCALIZATION_INLINE_RE.search(description)
    if inline_match:
        return " ".join(inline_match.group("section").split()).lower()

    lines = description.splitlines()
    for idx, line in enumerate(lines):
        if not LOCALIZATION_HEADING_RE.match(line):
            continue

        collected: list[str] = []
        for next_line in lines[idx + 1 :]:
            stripped = next_line.strip()
            if MARKDOWN_HEADING_RE.match(next_line) or COLON_HEADING_RE.match(next_line):
                break
            if not stripped:
                if collected:
                    break
                continue
            collected.append(stripped)

        return " ".join(collected).lower()

    return ""


def _classify_from_remote_scope(scope_l: str) -> Dict | None:
    if not scope_l:
        return None

    parts = re.split(r"[;,/]+", scope_l)
    tokens = [_normalize_token(p) for p in parts if p.strip()]

    found_eu = False
    found_non_eu = False

    for token in tokens:
        if token in COUNTRY_ALIASES:
            mapped_full_name = COUNTRY_ALIASES[token].lower()
            if mapped_full_name in EU_MEMBER_STATES:
                found_eu = True
            else:
                found_non_eu = True
            continue

        if token in EU_MEMBER_STATES:
            found_eu = True
            continue

        if token in UK_KEYWORDS:
            found_eu = True
            continue

    if found_eu and found_non_eu:
        return {"geo_class": GeoClass.EU_REGION, "reason": "mixed_region"}
    if found_eu:
        return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": "explicit_country"}
    if found_non_eu:
        return {"geo_class": GeoClass.NON_EU, "reason": "explicit_country"}

    return None


def _classify_from_localization_section(description: str) -> Dict | None:
    localization_text = _extract_localization_section(description)
    if not localization_text:
        return None

    for country in EU_MEMBER_STATES:
        if _contains_phrase(localization_text, country):
            return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": country}

    # Ignore 2-letter aliases in free text to reduce false positives.
    for alias, mapped in COUNTRY_ALIASES.items():
        if len(alias) <= 2:
            continue
        if _contains_phrase(localization_text, alias):
            mapped_full_name = mapped.lower()
            if mapped_full_name in EU_MEMBER_STATES:
                return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": mapped_full_name}

    for kw in UK_KEYWORDS:
        if _contains_phrase(localization_text, kw):
            return {"geo_class": GeoClass.UK, "reason": kw}

    return None


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
    # 1 Hard non-EU regions (highest priority)
    # ------------------------------------------------------------
    for kw in NON_EU_REGION_CUSTOM:
        if kw in scope_l or kw in title_l:
            return {"geo_class": GeoClass.NON_EU, "reason": kw}

    # ------------------------------------------------------------
    # 2 EU region custom keywords (EMEA, Nordics, Western Europe, UK&I)
    # ------------------------------------------------------------
    for kw in EU_REGION_CUSTOM:
        if kw in scope_l or kw in title_l:
            return {"geo_class": GeoClass.EU_REGION, "reason": kw}

    # ------------------------------------------------------------
    # 3 Structured parsing of remote_scope (most reliable source for countries)
    # ------------------------------------------------------------
    scope_result = _classify_from_remote_scope(scope_l)
    if scope_result:
        return scope_result

    # ------------------------------------------------------------
    # 4 Fallback to the "Localization" section from description only
    # ------------------------------------------------------------
    localization_result = _classify_from_localization_section(description or "")
    if localization_result:
        return localization_result

    # ------------------------------------------------------------
    # 5 UK fallback in generic text
    # ------------------------------------------------------------
    for kw in UK_KEYWORDS:
        if _contains_phrase(full_text, kw):
            return {"geo_class": GeoClass.UK, "reason": kw}

    # ------------------------------------------------------------
    # 6 Unknown
    # ------------------------------------------------------------
    return {"geo_class": GeoClass.UNKNOWN, "reason": None}
