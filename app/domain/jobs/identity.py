import hashlib
import re
from typing import Any


_WHITESPACE_RE = re.compile(r"\s+")

def normalize(text: Any) -> str:
    text = str(text or "")
    text = text.lower()
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.strip()
    return text


def compute_job_uid(company_id: str | None, title: str, location: str | None) -> str:
    title = normalize(title or "")
    location = normalize(location or "")

    base = f"{company_id or ''}|{title}|{location}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def compute_job_fingerprint(
    description: str,
    *,
    title: str = "",
    location: str | None = None,
    company_id: str | None = None,
    company_name: str = "",
) -> str:
    title = normalize(title or "")
    location = normalize(location or "")
    company_id = normalize(company_id or "")
    company_name = normalize(company_name or "")

    # Optymalizacja: Ograniczamy opis ZANIM przemieli go potężny regex
    # Bufor 1500 znaków z zapasem wystarczy, by po usunięciu spacji zostało 500 znaków.
    raw_fragment = str(description or "").strip()[:1500]
    fragment = normalize(raw_fragment)[:500]

    base = f"{company_id}|{company_name}|{title}|{location}|{fragment}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def _schema_signature(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value.keys(), key=str):
            parts.append(f"{key}:{_schema_signature(value[key])}")
        return "{" + ",".join(parts) + "}"

    if isinstance(value, list):
        if not value:
            return "list[]"
        item_signatures = sorted({_schema_signature(item) for item in value})
        return "list[" + ",".join(item_signatures) + "]"

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"

    return type(value).__name__


def compute_schema_hash(raw_payload: Any) -> str:
    signature = _schema_signature(raw_payload)
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def compute_job_identity(
    company_id: str | None,
    raw_job: dict,
    normalized_job: dict,
) -> dict:
    """
    Computes UID, fingerprint and schema hash for a normalized job.
    This is pure domain logic related to job identity.
    """
    resolved_company_id = company_id or normalized_job.get("company_id")
    if not resolved_company_id:
        raise ValueError("Missing company_id for job identity")

    title = (normalized_job.get("title") or "").strip()
    location = (normalized_job.get("remote_scope") or "").strip()
    description = (normalized_job.get("description") or "").strip()

    # Stable identity (must not change when job text changes)
    normalized_job["job_uid"] = compute_job_uid(
        company_id=resolved_company_id,
        title=title,
        location=location,
    )

    # Content fingerprint (detects edits in job description)
    normalized_job["job_fingerprint"] = compute_job_fingerprint(
        description,
        title=title,
        location=location,
        company_id=resolved_company_id,
        company_name=(normalized_job.get("company_name") or "").strip(),
    )

    # Detect ATS schema changes
    normalized_job["source_schema_hash"] = compute_schema_hash(raw_job)

    return normalized_job
