import re
from typing import Dict, List

from app.workers.policy.v2.geo_data import COUNTRY_ALIASES, EU_MEMBER_STATES


def _normalize_token(tok: str) -> str:
    tok = tok.strip().lower()
    # remove surrounding parentheses and stray dots
    tok = tok.strip('()').strip()
    tok = tok.rstrip('.')
    return tok


def classify_geo_from_remote_scope(remote_scope: str) -> Dict:
    """Classify a remote scope string into EU/non-EU categories.

    Returns a dict with keys:
      - classification: one of 'eu_explicit', 'non_eu', 'eu_region', 'unknown'
      - isos: list of discovered ISO codes (lowercase)
      - eu_isos: list of ISO codes identified as EU members
    """
    REGION_KEYWORDS = [
    "western europe",
    "europe",
    "eu",
    "european union",
    "eea",
    "european economic area",
    "eu/eea",
    "eu and eea",
    "eu/eea region",
    "eu/eea countries",
    "eu/eea member states",
    "eu/eea region",
    "eu/eea area",
    "eu/eea zone",
    "eu/eea territory",
    "eu/eea jurisdiction",
    "eu/eea market",]

    lower_scope = remote_scope.lower()

    for kw in REGION_KEYWORDS:
        if kw in lower_scope:
            return {
                "classification": "eu_region",
                "isos": [],
                "eu_isos": [],
            }



    if not remote_scope:
        return {"classification": "unknown", "isos": [], "eu_isos": []}

    # split on ; , /
    parts = re.split(r"[;,/]+", remote_scope)
    tokens = [_normalize_token(p) for p in parts if p and p.strip()]

    found_isos = set()

    # derive EU ISO set from COUNTRY_ALIASES by checking which alias keys are in
    # EU_MEMBER_STATES (EU_MEMBER_STATES uses full lowercase country names)
    eu_iso_set = set()
    for alias, iso in COUNTRY_ALIASES.items():
        if alias in EU_MEMBER_STATES:
            eu_iso_set.add(iso.lower())

    for t in tokens:
        iso = None
        if not t:
            continue
        # direct alias mapping
        if t in COUNTRY_ALIASES:
            iso = COUNTRY_ALIASES[t].lower()
        # two-letter ISO code provided directly
        elif len(t) == 2 and t.isalpha():
            iso = t.lower()
        # token matches a full country name present in EU_MEMBER_STATES
        elif t in EU_MEMBER_STATES:
            # try to find an alias that maps this country name to an ISO
            if t in COUNTRY_ALIASES:
                iso = COUNTRY_ALIASES[t].lower()
            else:
                # no mapping available - skip
                iso = None
        # otherwise, try to match some common alias forms (strip plurals)
        else:
            # attempt a direct lookup after trimming common words
            cleaned = t.replace("the ", "").strip()
            if cleaned in COUNTRY_ALIASES:
                iso = COUNTRY_ALIASES[cleaned].lower()

        if iso:
            found_isos.add(iso)

    eu_isos = sorted([i for i in found_isos if i in eu_iso_set])
    non_eu_isos = sorted([i for i in found_isos if i not in eu_iso_set])

    if eu_isos and non_eu_isos:
        classification = "eu_region"
    elif eu_isos and not non_eu_isos:
        classification = "eu_explicit"
    elif non_eu_isos and not eu_isos:
        classification = "non_eu"
    else:
        classification = "unknown"

    return {"classification": classification, "isos": sorted(found_isos), "eu_isos": eu_isos}
