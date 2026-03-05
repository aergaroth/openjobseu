import hashlib
import re
from typing import Any


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def compute_job_uid(company_id: str | None, title: str, location: str | None, description: str) -> str:
    title = normalize(title or "")
    location = normalize(location or "")
    description = normalize(description or "")
    description_fragment = description[:200]

    base = f"{company_id or ''}|{title}|{location}|{description_fragment}"
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
    description = normalize(description or "")
    fragment = description[:500]

    base = f"{company_id}|{company_name}|{title}|{location}|{fragment}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _schema_signature(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            parts.append(f"{key_text}:{_schema_signature(value[key])}")
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
