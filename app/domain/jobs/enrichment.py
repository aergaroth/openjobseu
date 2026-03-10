import logging

from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.classification.mappers import normalize_geo_class, normalize_remote_class
from app.domain.classification.taxonomy import classify_taxonomy
from app.domain.compliance.engine import ENGINE_POLICY_VERSION, apply_policy
from app.domain.jobs.identity import (
    compute_job_fingerprint,
    compute_job_uid,
    compute_schema_hash,
)
from app.domain.money.salary_parser import extract_salary
from app.domain.money.structured_salary import extract_structured_salary
from app.domain.money.transparency import detect_salary_transparency

logger = logging.getLogger(__name__)


def _string_like(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def enrich_and_apply_policy(
    job: dict,
    *,
    raw_job: dict,
    company_id: str,
    source: str,
) -> tuple[dict | None, str | None]:
    """
    Enriches a normalized job with identity, applies compliance policy,
    and adds further enrichments like taxonomy and salary.
    """
    # 1. Enrich with identity
    title = (job.get("title") or "").strip()
    location = (job.get("remote_scope") or "").strip()
    description = (job.get("description") or "").strip()

    job["job_uid"] = compute_job_uid(company_id=company_id, title=title, location=location)
    job["job_fingerprint"] = compute_job_fingerprint(
        description,
        title=title,
        location=location,
        company_id=company_id,
        company_name=(job.get("company_name") or "").strip(),
    )
    job["source_schema_hash"] = compute_schema_hash(raw_job)

    # 2. Apply compliance policy
    job_after_policy, reason = apply_policy(job, source=source)

    if not job_after_policy:
        return None, reason

    # 3. Further enrichment post-policy (only if approved)
    enriched_job = job_after_policy
    compliance_payload = enriched_job.get("_compliance") or {}
    compliance_status = compliance_payload.get("compliance_status")

    if compliance_status == "approved":
        # Taxonomy
        taxonomy = classify_taxonomy(str(enriched_job.get("title") or ""))
        enriched_job.update(taxonomy)

        # Salary
        salary_info = {}
        structured = extract_structured_salary(enriched_job)
        if structured:
            salary_info = structured
        else:
            regex_salary = extract_salary(enriched_job.get("description") or "")
            if regex_salary:
                salary_info = regex_salary
        enriched_job.update(salary_info)

        salary_detected = bool(salary_info.get("salary_min") is not None or salary_info.get("salary_max") is not None)
        transparency_status = detect_salary_transparency(
            enriched_job.get("description") or "", salary_detected
        )
        enriched_job["salary_transparency_status"] = transparency_status
        if salary_info:
            logger.info(f"salary_{salary_info.get('salary_source')}_detected", extra={"job_id": enriched_job.get("job_id")})
        else:
            logger.info("salary_missing", extra={"job_id": enriched_job.get("job_id")})
    else:
        # Defaults for rejected/other status
        enriched_job["salary_transparency_status"] = None

    # Compliance fields
    compliance_payload = enriched_job.get("_compliance") or {}
    enriched_job["remote_class"] = normalize_remote_class(_string_like(compliance_payload.get("remote_model"))).value
    enriched_job["geo_class"] = normalize_geo_class(_string_like(compliance_payload.get("geo_class"))).value
    enriched_job["compliance_status"] = compliance_payload.get("compliance_status")
    enriched_job["compliance_score"] = compliance_payload.get("compliance_score")

    # Policy version
    policy_version = _string_like(compliance_payload.get("policy_version"))
    enriched_job["policy_version"] = policy_version or ENGINE_POLICY_VERSION.value

    return enriched_job, reason