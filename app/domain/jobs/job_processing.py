from typing import Optional, Tuple

from app.domain.jobs.mappers import normalize_geo_class, normalize_remote_class
from app.domain.taxonomy.taxonomy import classify_taxonomy
from app.domain.compliance.engine import ENGINE_POLICY_VERSION, apply_policy
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
)
from app.domain.jobs.canonical_identity import compute_canonical_job_id
from app.domain.money.salary_parser import extract_salary
from app.domain.money.structured_salary import extract_structured_salary
from app.domain.money.transparency import detect_salary_transparency
from app.domain.jobs.quality_score import compute_job_quality_score


def _string_like(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def process_ingested_job(job: dict, source: str) -> Tuple[Optional[dict], dict]:
    """
    Core domain logic for processing a single ingested job.
    Transforms data, applies compliance, taxonomy, salary extraction and scoring.
    Does NOT perform any IO.

    Returns:
        tuple: (processed_job_dict or None, compliance_report_dict)
    """
    # 1. Identity
    title = (job.get("title") or "").strip()
    location = (job.get("remote_scope") or "").strip()
    description = (job.get("description") or "").strip()
    company_id = job.get("company_id")
    company_name = (job.get("company_name") or "").strip()

    # Canonical cross-ATS identity for persisted jobs
    job["job_id"] = compute_canonical_job_id(job)

    if "job_uid" not in job:
        job["job_uid"] = compute_job_uid(company_id=company_id, title=title, location=location)

    if "job_fingerprint" not in job:
        job["job_fingerprint"] = compute_job_fingerprint(
            description,
            title=title,
            location=location,
            company_id=company_id,
            company_name=company_name,
        )

    # 2. Compliance
    job_after_policy, reason = apply_policy(job, source=source)

    compliance_payload = (job_after_policy or job).get("_compliance") or {}

    # Prepare compliance report (always returned)
    compliance_report = {
        "job_uid": str(job.get("job_uid")),
        "policy_version": _string_like(compliance_payload.get("policy_version")) or ENGINE_POLICY_VERSION.value,
        "remote_class": compliance_payload.get("remote_model"),
        "geo_class": compliance_payload.get("geo_class"),
        "hard_geo_flag": bool(compliance_payload.get("policy_reason") == "geo_restriction_hard"),
        "base_score": compliance_payload.get("compliance_score"),
        "penalties": None,
        "bonuses": None,
        "final_score": compliance_payload.get("compliance_score"),
        "final_status": compliance_payload.get("compliance_status"),
        "decision_vector": compliance_payload.get("decision_trace"),
        "policy_reason": reason,
    }

    if not job_after_policy:
        return None, compliance_report

    processed_job = job_after_policy

    # 3. Taxonomy
    taxonomy = classify_taxonomy(
        title=str(processed_job.get("title") or ""),
        department=processed_job.get("department"),
    )
    processed_job.update(taxonomy)

    # 4. Salary
    salary_info = extract_structured_salary(processed_job)
    if not salary_info:
        salary_info = extract_salary(
            processed_job.get("description") or "",
            title=processed_job.get("title") or "",
        )
        if salary_info:
            # Oznacz trudne przypadki do manualnej weryfikacji
            confidence = salary_info.get("salary_confidence")
            if confidence is not None and confidence < 80:
                processed_job["_salary_parsing_case"] = salary_info

    if salary_info:
        processed_job.update(salary_info)
    else:
        salary_info = {}

    salary_detected = bool(salary_info.get("salary_min") is not None or salary_info.get("salary_max") is not None)
    processed_job["salary_transparency_status"] = detect_salary_transparency(
        processed_job.get("description") or "", salary_detected
    )

    # 5. Quality Score
    processed_job["job_quality_score"] = compute_job_quality_score(processed_job)

    # 6. Normalize fields for storage
    processed_job["remote_class"] = normalize_remote_class(_string_like(compliance_payload.get("remote_model"))).value
    processed_job["geo_class"] = normalize_geo_class(_string_like(compliance_payload.get("geo_class"))).value
    processed_job["compliance_status"] = compliance_payload.get("compliance_status")
    processed_job["compliance_score"] = compliance_payload.get("compliance_score")
    processed_job["policy_version"] = compliance_report["policy_version"]

    return processed_job, compliance_report
