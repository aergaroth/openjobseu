from typing import Tuple

from app.workers.policy.v3.remote_v3 import classify_remote_v3
from app.workers.policy.v3.geo_v3 import classify_geo_v3
from app.workers.policy.v3.hard_geo_detector import detect_hard_geo_restriction


def apply_policy_v3(job: dict, source: str) -> Tuple[dict | None, str | None]:

    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    remote_scope = str(job.get("remote_scope") or "")

    combined = f"{title} {description} {remote_scope}"

    # 1 HARD GEO
    if detect_hard_geo_restriction(combined):
        job["_compliance"] = {
            "policy_version": "v3",
            "policy_reason": "geo_restriction_hard",
            "remote_model": "unknown",
            "geo_class": "non_eu",
        }
        return job, "geo_restriction_hard"

    # 2 Remote classification
    remote_result = classify_remote_v3(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )

    # 3 Geo classification
    geo_result = classify_geo_v3(
        title=title,
        description=description,
        remote_scope=remote_scope,
    )

    job["_compliance"] = {
        "policy_version": "v3",
        "policy_reason": None,
        "remote_model": remote_result["remote_model"],
        "geo_class": geo_result["geo_class"],
        "remote_reason": remote_result["reason"],
        "geo_reason": geo_result["reason"],
    }

    return job, None