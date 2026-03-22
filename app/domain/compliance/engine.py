import hashlib
from pathlib import Path
from enum import Enum

from app.domain.taxonomy.enums import ComplianceStatus, GeoClass, RemoteClass
from app.domain.compliance.classifiers.geo import classify_geo
from app.domain.compliance.classifiers.hard_geo import detect_hard_geo_restriction
from app.domain.compliance.classifiers.remote import classify_remote
from app.domain.compliance.resolver import resolve_compliance


def _compute_compliance_version() -> str:
    base_version = "v4"
    compliance_dir = Path(__file__).parent

    hasher = hashlib.md5()

    # Sort files to ensure deterministic hashing across different operating systems
    for file_path in sorted(compliance_dir.rglob("*.py")):
        try:
            content = file_path.read_text(encoding="utf-8")
            # Normalize line endings to avoid hash mismatch between Windows (CRLF) and Linux/Mac (LF)
            content = content.replace("\r\n", "\n")
            hasher.update(content.encode("utf-8"))
        except OSError:
            pass

    short_hash = hasher.hexdigest()[:7]
    return f"{base_version}.{short_hash}"


class PolicyVersion(str, Enum):
    V4 = _compute_compliance_version()


ENGINE_POLICY_VERSION = PolicyVersion.V4
# Backward-compatible alias.
ENGINE_VERSION = ENGINE_POLICY_VERSION.value


def apply_policy(job: dict, source: str) -> tuple[dict | None, str | None]:
    # Ensure _compliance is always initialized
    if "_compliance" not in job:
        job["_compliance"] = {
            "policy_version": ENGINE_POLICY_VERSION.value,
            "policy_reason": "initialization_failure",
            "remote_model": RemoteClass.UNKNOWN,
            "geo_class": GeoClass.UNKNOWN,
            "source": source,
        }

    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    remote_scope = str(job.get("remote_scope") or "")

    combined = f"{title} {description} {remote_scope}"
    trace = []

    # 1 Hard geo restrictions
    hard_geo = detect_hard_geo_restriction(combined)
    trace.append({"step": "hard_geo_check", "result": hard_geo})

    if hard_geo:
        job["_compliance"] = {
            "policy_version": ENGINE_POLICY_VERSION.value,
            "policy_reason": "geo_restriction_hard",
            "remote_model": RemoteClass.UNKNOWN,
            "geo_class": GeoClass.NON_EU,
            "compliance_score": 0,
            "compliance_status": ComplianceStatus.REJECTED.value,
            "decision_trace": trace,
        }
        return job, "geo_restriction_hard"

    # 2 Remote classification
    remote_result = classify_remote(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )
    remote_model = remote_result["remote_model"]
    trace.append(
        {
            "step": "remote_classifier",
            "result": remote_model.value if hasattr(remote_model, "value") else remote_model,
            "reason": remote_result["reason"],
        }
    )

    # 3 Geo classification
    geo_result = classify_geo(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )
    geo_class = geo_result["geo_class"]
    trace.append(
        {
            "step": "geo_classifier",
            "result": geo_class.value if hasattr(geo_class, "value") else geo_class,
            "reason": geo_result["reason"],
        }
    )

    # 4 Resolution
    resolved = resolve_compliance(remote_model, geo_class)
    score = resolved["compliance_score"]
    status = resolved["compliance_status"]

    # 5 Scoring trace
    penalties = []
    if remote_model != RemoteClass.REMOTE_ONLY:
        penalties.append(remote_model.value if hasattr(remote_model, "value") else remote_model)

    if geo_class not in {GeoClass.EU_MEMBER_STATE, GeoClass.EU_EXPLICIT}:
        penalties.append(geo_class.value if hasattr(geo_class, "value") else geo_class)

    trace.append({"step": "scoring", "score": score, "penalties": penalties, "bonuses": []})

    # 6 Resolver trace
    trace.append({"step": "resolver", "status": status})

    job["_compliance"] = {
        "policy_version": ENGINE_POLICY_VERSION.value,
        "policy_reason": None,
        "remote_model": remote_model,
        "geo_class": geo_class,
        "remote_reason": remote_result["reason"],
        "geo_reason": geo_result["reason"],
        "compliance_score": score,
        "compliance_status": status,
        "decision_trace": trace,
        "source": source,
    }

    return job, None


def apply_policy_v3(job: dict, source: str) -> tuple[dict | None, str | None]:
    return apply_policy(job=job, source=source)
