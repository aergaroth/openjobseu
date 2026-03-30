import re
from html import unescape

from app.domain.jobs.enums import GeoClass
from app.domain.compliance.classifiers.geo_data import (
    APAC_STRONG_SIGNALS,
    AUSTRALIA_STRONG_SIGNALS,
    CANADA_STRONG_SIGNALS,
    COUNTRY_ALIASES,
    EOG_COUNTRIES,
    EU_MEMBER_STATES,
    EU_REGION_CUSTOM,
    EU_REGION_KEYWORDS,
    INDIA_STRONG_SIGNALS,
    LATAM_STRONG_SIGNALS,
    NON_EU_RESTRICTED,
    NON_EU_REGION_CUSTOM,
    NON_EU_SCOPE_TITLE_PHRASES,
    NON_EU_SCOPE_TOKENS,
    US_STATE_CODES,
    US_STATE_SIGNAL_THRESHOLD,
    US_STRONG_SIGNALS,
    UK_KEYWORDS,
)

HTML_LOCALIZATION_SECTION_RE = re.compile(
    r"(?is)<h[1-6][^>]*>\s*locali[sz]ation\s*:?\s*</h[1-6]>\s*(?P<section>.*?)(?=<h[1-6][^>]*>|$)"
)
HTML_TAG_RE = re.compile(r"(?is)<[^>]+>")
LOCALIZATION_INLINE_RE = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?locali[sz]ation\s*:\s*(?P<section>.+)$")
LOCALIZATION_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s*)?locali[sz]ation\s*:?\s*$", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
COLON_HEADING_RE = re.compile(r"^\s*[A-Za-z][A-Za-z0-9 /&()+-]{1,60}\s*:\s*$")
US_STATE_CODES_RE = re.compile(
    r"\b(?:" + "|".join(code.upper() for code in US_STATE_CODES) + r")\b",
    re.IGNORECASE,
)


def _normalize_token(tok: str) -> str:
    return tok.strip().lower().strip("()").rstrip(".")


def _contains_phrase(full_text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", full_text) is not None


def _count_us_state_signal_hits(full_text: str) -> int:
    hits = {match.group(0).lower() for match in US_STATE_CODES_RE.finditer(full_text)}
    return len(hits)


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


def _classify_from_remote_scope(scope_l: str) -> dict | None:
    if not scope_l:
        return None

    parts = re.split(r"[;,/]+", scope_l)
    tokens = [_normalize_token(p) for p in parts if p.strip()]

    found_eu = False
    found_non_eu = False

    if any(_contains_phrase(scope_l, kw) for kw in NON_EU_SCOPE_TITLE_PHRASES):
        found_non_eu = True

    if any(_contains_phrase(scope_l, kw) for kw in US_STRONG_SIGNALS):
        found_non_eu = True

    for token in tokens:
        if token in US_STATE_CODES:
            found_non_eu = True
            continue

        if token in COUNTRY_ALIASES:
            mapped_full_name = COUNTRY_ALIASES[token].lower()
            if mapped_full_name in EU_MEMBER_STATES or mapped_full_name in EOG_COUNTRIES:
                found_eu = True
            else:
                found_non_eu = True
            continue

        if token in EU_MEMBER_STATES or token in EOG_COUNTRIES:
            found_eu = True
            continue

        if token in UK_KEYWORDS:
            found_eu = True
            continue

        # Handle mixed free-form scopes, e.g. "Remote - US: Select locations".
        token_parts = [_normalize_token(part) for part in re.split(r"[\s:\-]+", token) if part.strip()]
        for token_part in token_parts:
            if token_part in US_STATE_CODES:
                found_non_eu = True
                continue
            if token_part in NON_EU_SCOPE_TOKENS:
                found_non_eu = True
                continue
            if token_part in COUNTRY_ALIASES:
                mapped = COUNTRY_ALIASES[token_part].lower()
                if mapped in EU_MEMBER_STATES or mapped in EOG_COUNTRIES:
                    found_eu = True
                else:
                    found_non_eu = True
                continue
            if token_part in EU_MEMBER_STATES or token_part in EOG_COUNTRIES:
                found_eu = True
                continue

    if found_eu and found_non_eu:
        return {"geo_class": GeoClass.EU_REGION, "reason": "mixed_region"}
    if found_eu:
        return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": "explicit_country"}
    if found_non_eu:
        return {"geo_class": GeoClass.NON_EU, "reason": "explicit_country"}

    return None


def _classify_from_localization_section(description: str) -> dict | None:
    localization_text = _extract_localization_section(description)
    if not localization_text:
        return None

    for country in EU_MEMBER_STATES:
        if _contains_phrase(localization_text, country):
            return {"geo_class": GeoClass.EU_MEMBER_STATE, "reason": country}

    for country in EOG_COUNTRIES:
        if _contains_phrase(localization_text, country):
            return {"geo_class": GeoClass.EU_REGION, "reason": country}

    # Ignore 2-letter aliases in free text to reduce false positives.
    for alias, mapped in COUNTRY_ALIASES.items():
        if len(alias) <= 2:
            continue
        if _contains_phrase(localization_text, alias):
            mapped_full_name = mapped.lower()
            if mapped_full_name in EU_MEMBER_STATES:
                return {
                    "geo_class": GeoClass.EU_MEMBER_STATE,
                    "reason": mapped_full_name,
                }
            if mapped_full_name in EOG_COUNTRIES:
                return {"geo_class": GeoClass.EU_REGION, "reason": mapped_full_name}

    for kw in UK_KEYWORDS:
        if _contains_phrase(localization_text, kw):
            return {"geo_class": GeoClass.UK, "reason": kw}

    return None


def classify_geo(
    *,
    title: str,
    description: str,
    remote_scope: str,
) -> dict:
    title_l = (title or "").lower()
    scope_l = (remote_scope or "").lower()
    desc_l = (description or "").lower()

    found_eu = False
    found_non_eu = False
    eu_result = None
    non_eu_reason = None
    non_eu_scope_title_phrase_hit = False
    non_eu_scope_title_phrase_reason = None

    # 1 Evaluate structural parse of scope and title together
    scope_result = _classify_from_remote_scope(scope_l)
    title_result = _classify_from_remote_scope(title_l)

    def _is_eu(res: dict | None) -> bool:
        return bool(res and res["geo_class"] in (GeoClass.EU_MEMBER_STATE, GeoClass.EU_REGION, GeoClass.UK))

    def _is_non_eu(res: dict | None) -> bool:
        return bool(res and res["geo_class"] == GeoClass.NON_EU)

    def _is_mixed(res: dict | None) -> bool:
        return bool(res and res.get("reason") == "mixed_region")

    for res in (scope_result, title_result):
        if _is_mixed(res):
            found_eu, found_non_eu = True, True
            eu_result = {"geo_class": GeoClass.EU_REGION, "reason": "mixed_region"}
        elif _is_eu(res):
            found_eu = True
            if not eu_result:
                eu_result = res
        elif _is_non_eu(res):
            found_non_eu = True
            if not non_eu_reason:
                non_eu_reason = res["reason"]

    # 2 Evaluate custom region keywords (EMEA vs APAC/LATAM)
    for kw in EU_REGION_CUSTOM:
        if kw in scope_l or kw in title_l:
            found_eu = True
            if not eu_result:
                eu_result = {"geo_class": GeoClass.EU_REGION, "reason": kw}

    for kw in NON_EU_REGION_CUSTOM:
        if kw in scope_l or kw in title_l:
            found_non_eu = True
            if not non_eu_reason:
                non_eu_reason = kw

    for kw in NON_EU_SCOPE_TITLE_PHRASES:
        if _contains_phrase(scope_l, kw) or _contains_phrase(title_l, kw):
            found_non_eu = True
            if not non_eu_reason:
                non_eu_reason = kw
            non_eu_scope_title_phrase_hit = True
            if not non_eu_scope_title_phrase_reason:
                non_eu_scope_title_phrase_reason = kw

    # 3 Mixed Region Resolution (Prevents False Negatives for "US & EMEA" etc.)
    if found_eu and found_non_eu:
        if non_eu_scope_title_phrase_hit:
            return {
                "geo_class": GeoClass.NON_EU,
                "reason": non_eu_scope_title_phrase_reason or non_eu_reason,
            }
        return {"geo_class": GeoClass.EU_REGION, "reason": "mixed_region"}
    if found_eu and eu_result:
        return eu_result
    if found_non_eu:
        return {"geo_class": GeoClass.NON_EU, "reason": non_eu_reason}

    # 4 Fallback to the "Localization" section from description
    localization_result = _classify_from_localization_section(description or "")
    if localization_result:
        return localization_result

    # 4.5 Safe regional and explicit fallback in full description
    # Catches strong constraints missed when remote_scope is empty
    for kw in EU_REGION_KEYWORDS:
        if _contains_phrase(desc_l, kw):
            return {"geo_class": GeoClass.EU_REGION, "reason": f"desc_{kw.replace(' ', '_')}"}

    for kw in EU_REGION_CUSTOM:
        if _contains_phrase(desc_l, kw):
            return {"geo_class": GeoClass.EU_REGION, "reason": f"desc_{kw.replace(' & ', '_').replace(' ', '_')}"}

    # Safely match explicit UK restrictions in text without triggering generic words like "London"
    for kw in ("uk only", "uk-based", "uk based", "remote in the uk", "remote uk", "remotely in the uk"):
        if _contains_phrase(desc_l, kw):
            return {"geo_class": GeoClass.UK, "reason": f"desc_{kw.replace(' ', '_')}"}

    # Hidden gem: Timezones commonly used for European roles
    for kw in ("cet", "cest", "utc+1", "utc +1", "utc+2", "utc +2"):
        if _contains_phrase(desc_l, kw):
            return {"geo_class": GeoClass.EU_REGION, "reason": f"desc_timezone_{kw.replace(' ', '')}"}

    # 5 UK fallback - apply ONLY to scope and title, NOT full description
    # (prevents false positives from generic text like "Our HQ is in London")
    scope_and_title = f"{title_l} {scope_l}"
    for kw in UK_KEYWORDS:
        if _contains_phrase(scope_and_title, kw):
            return {"geo_class": GeoClass.UK, "reason": kw}

    # 6 Unknown
    return {"geo_class": GeoClass.UNKNOWN, "reason": None}


def classify_geo_v3(*, title: str, description: str, remote_scope: str) -> dict:
    return classify_geo(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )


def classify_geo_scope(title: str, description: str) -> dict:
    full_text = f"{title or ''} {description or ''}".lower()

    # 1 Hard non-EU restrictions first
    for kw in US_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in CANADA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in APAC_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in AUSTRALIA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in INDIA_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in LATAM_STRONG_SIGNALS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    for kw in NON_EU_RESTRICTED:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.NON_EU.value,
                "matched_keyword": kw,
            }

    # 2) US states by abbreviation (>=3) => non-EU
    us_state_hits = _count_us_state_signal_hits(full_text)
    if us_state_hits >= US_STATE_SIGNAL_THRESHOLD:
        return {
            "geo_class": GeoClass.NON_EU.value,
            "matched_keyword": f"us_state_codes>={US_STATE_SIGNAL_THRESHOLD}",
        }

    # 3) Explicit EU mention
    if (
        _contains_phrase(full_text, "eu only")
        or _contains_phrase(full_text, "eu-only")
        or _contains_phrase(full_text, "european union")
    ):
        return {
            "geo_class": GeoClass.EU_EXPLICIT.value,
            "matched_keyword": "eu",
        }

    # 4) EU member states
    for country in EU_MEMBER_STATES:
        if _contains_phrase(full_text, country):
            return {
                "geo_class": GeoClass.EU_MEMBER_STATE.value,
                "matched_keyword": country,
            }

    # 5) EOG / EEA region
    for country in EOG_COUNTRIES:
        if _contains_phrase(full_text, country):
            return {
                "geo_class": GeoClass.EU_REGION.value,
                "matched_keyword": country,
            }
    for kw in EU_REGION_KEYWORDS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.EU_REGION.value,
                "matched_keyword": kw,
            }

    # 6) UK
    for kw in UK_KEYWORDS:
        if _contains_phrase(full_text, kw):
            return {
                "geo_class": GeoClass.UK.value,
                "matched_keyword": kw,
            }
    if re.search(r"\buk\b", full_text):
        return {
            "geo_class": GeoClass.UK.value,
            "matched_keyword": GeoClass.UK.value,
        }

    # 7) Fallback
    return {
        "geo_class": GeoClass.UNKNOWN.value,
        "matched_keyword": None,
    }
