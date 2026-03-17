import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")

def _normalize(value: str | None) -> str:
    text = (value or "").lower().strip()
    return _WHITESPACE_RE.sub(" ", text)


def compute_canonical_job_id(job: dict) -> str:
    company = _normalize(job.get("company_name"))
    title = _normalize(job.get("title"))
    
    # Optymalizacja: ucinamy opis przed procesowaniem (bufor 3000 znaków)
    raw_desc = str(job.get("description") or "")[:3000]
    description = _normalize(raw_desc)[:1000]

    hash_input = f"{company}|{title}|{description}"
    return hashlib.sha1(hash_input.encode("utf-8")).hexdigest()
