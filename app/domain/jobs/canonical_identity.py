import hashlib
import re


def _normalize(value: str | None) -> str:
    text = (value or "").lower().strip()
    return re.sub(r"\s+", " ", text)


def compute_canonical_job_id(job: dict) -> str:
    company = _normalize(job.get("company_name"))
    title = _normalize(job.get("title"))
    description = _normalize(job.get("description"))[:1000]

    hash_input = f"{company}|{title}|{description}"
    return hashlib.sha1(hash_input.encode("utf-8")).hexdigest()
