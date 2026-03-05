from app.domain.classification.enums import GeoClass, RemoteClass
from app.domain.compliance.engine import apply_policy


def _job(*, title: str, description: str, remote_scope: str) -> dict:
    return {
        "job_id": "seed:1",
        "source": "employer_ing",
        "source_job_id": "1",
        "source_url": "https://example.com/jobs/1",
        "title": title,
        "company_name": "Acme",
        "description": description,
        "remote_source_flag": True,
        "remote_scope": remote_scope,
        "status": "new",
        "first_seen_at": "2026-01-05T10:00:00+00:00",
    }


def test_apply_policy_sets_remote_and_geo_models_for_standard_remote_job():
    job = _job(
        title="Backend Engineer",
        description="Build APIs for our distributed team.",
        remote_scope="Poland",
    )

    result, reason = apply_policy(job, source="employer_ing")

    assert reason is None
    assert result is not None
    assert result["_compliance"]["policy_reason"] is None
    assert result["_compliance"]["remote_model"] in {
        RemoteClass.REMOTE_ONLY,
        RemoteClass.REMOTE_REGION_LOCKED,
        RemoteClass.UNKNOWN,
    }
    assert result["_compliance"]["geo_class"] in {
        GeoClass.EU_MEMBER_STATE,
        GeoClass.EU_REGION,
        GeoClass.UNKNOWN,
    }


def test_apply_policy_hard_geo_restriction_sets_rejection_reason():
    job = _job(
        title="Backend Engineer",
        description="Candidates outside the US will not be considered.",
        remote_scope="",
    )

    result, reason = apply_policy(job, source="employer_ing")

    assert result is not None
    assert reason == "geo_restriction_hard"
    assert result["_compliance"]["policy_reason"] == "geo_restriction_hard"
    assert result["_compliance"]["geo_class"] == GeoClass.NON_EU
