from typing import Dict, Optional, Tuple

from app.domain.taxonomy.enums import GeoClass, RemoteClass
from app.domain.taxonomy.mappers import normalize_geo_class, normalize_remote_class
from app.domain.taxonomy.taxonomy import classify_taxonomy
from app.domain.compliance.engine import ENGINE_POLICY_VERSION, apply_policy
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
    compute_schema_hash,
)
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

    job["job_uid"] = compute_job_uid(company_id=company_id, title=title, location=location)
    job["job_fingerprint"] = compute_job_fingerprint(
        description,
        title=title,
        location=location,
        company_id=company_id,
        company_name=company_name,
    )
    # Note: source_schema_hash should be computed before normalization 
    # but since we receive normalized job here, we assume it's already in the dict 
    # or will be handled if raw_job was available. 
    # For now, we preserve the flow where worker might have set it or we use a placeholder.

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
        "final_score": compliance_payload.get("compliance_score"),
        "final_status": compliance_payload.get("compliance_status"),
        "decision_vector": compliance_payload.get("decision_trace"),
        "policy_reason": reason
    }

    if not job_after_policy or compliance_payload.get("compliance_status") != "approved":
        # Finalize normalized fields even for rejected jobs if they exist
        if job_after_policy:
            job_after_policy["remote_class"] = normalize_remote_class(_string_like(compliance_payload.get("remote_model"))).value
            job_after_policy["geo_class"] = normalize_geo_class(_string_like(compliance_payload.get("geo_class"))).value
            job_after_policy["compliance_status"] = compliance_payload.get("compliance_status")
            job_after_policy["compliance_score"] = compliance_payload.get("compliance_score")
            job_after_policy["policy_version"] = compliance_report["policy_version"]
            job_after_policy["salary_transparency_status"] = None
        return None, compliance_report

    processed_job = job_after_policy

    # 3. Taxonomy
    taxonomy = classify_taxonomy(str(processed_job.get("title") or ""))
    processed_job.update(taxonomy)

    # 4. Salary
    salary_info = {}
    structured = extract_structured_salary(processed_job)
    if structured:
        salary_info = structured
    else:
        regex_salary = extract_salary(processed_job.get("description") or "")
        if regex_salary:
            salary_info = regex_salary
    processed_job.update(salary_info)

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
