from enum import Enum

from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.compliance.classifiers.geo import classify_geo
from app.domain.compliance.classifiers.hard_geo import detect_hard_geo_restriction
from app.domain.compliance.classifiers.remote import classify_remote


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

    # 1 Hard geo restrictions
    if detect_hard_geo_restriction(combined):
        job["_compliance"] = {
            "policy_version": ENGINE_POLICY_VERSION.value,
            "policy_reason": "geo_restriction_hard",
            "remote_model": RemoteClass.UNKNOWN,
            "geo_class": GeoClass.NON_EU,
        }
        return job, "geo_restriction_hard"

    # 2 Remote classification
    remote_result = classify_remote(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )

    # 3 Geo classification
    geo_result = classify_geo(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )

    job["_compliance"] = {
        "policy_version": ENGINE_POLICY_VERSION.value,
        "policy_reason": None,
        "remote_model": remote_result["remote_model"],
        "geo_class": geo_result["geo_class"],
        "remote_reason": remote_result["reason"],
        "geo_reason": geo_result["reason"],
        "source": source,
    }

    return job, None


def apply_policy_v3(job: dict, source: str) -> tuple[dict | None, str | None]:
    return apply_policy(job=job, source=source)
