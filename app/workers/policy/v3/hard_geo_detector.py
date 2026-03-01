import re

HARD_GEO_PATTERNS = [
    r"\bus only\b",
    r"\bunited states only\b",
    r"\bmust be located in the us\b",
    r"\bmust reside in the us\b",
    r"\bus residents only\b",
    r"\bus applicants only\b",
    r"\bmust be authorized to work in the us\b",
    r"\bus work authorization required\b",
    r"\beligible to work in the us only\b",
    r"\bamericas only\b",
    r"\bnorth america only\b",
    r"\bsouth america only\b",
    r"\blatam only\b",
    r"\bcanada only\b",
    r"\bus or canada only\b",
    r"\bnot eligible outside the us\b",
    r"\bcandidates outside the us will not be considered\b",
    r"\bus payroll only\b",
    r"\bmust be eligible to work in the united states\b",
    r"\beligible to work in the united states\b",
    r"\bus citizenship required\b",
    r"\bus citizen required\b",
    r"\bus citizens only\b",
    r"\bus permanent resident required\b",
    r"\bgreen card required\b",
    r"\bmust have us work authorization\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in HARD_GEO_PATTERNS]


def detect_hard_geo_restriction(text: str) -> bool:
    if not text:
        return False

    normalized = text.lower()
    for pattern in COMPILED_PATTERNS:
        if pattern.search(normalized):
            return True

    return False
