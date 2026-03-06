from enum import Enum

from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.compliance.classifiers.geo import classify_geo
from app.domain.compliance.classifiers.hard_geo import detect_hard_geo_restriction
from app.domain.compliance.classifiers.remote import classify_remote
from app.domain.compliance.resolver import resolve_compliance


class PolicyVersion(str, Enum):
    V3 = "v3"


ENGINE_POLICY_VERSION = PolicyVersion.V3
# Backward-compatible alias.
ENGINE_VERSION = ENGINE_POLICY_VERSION.value


def apply_policy(job: dict, source: str) -> tuple[dict | None, str | None]:
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

    trace.append(
        {"step": "scoring", "score": score, "penalties": penalties, "bonuses": []}
    )

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
