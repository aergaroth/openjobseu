import pytest

from app.domain.taxonomy.enums import GeoClass, RemoteClass
from app.domain.compliance.engine import apply_policy


def _job(remote_scope: str, description: str = "", title: str = "Backend Engineer") -> dict:
    return {
        "title": title,
        "description": description,
        "remote_scope": remote_scope,
    }


@pytest.mark.parametrize(
    "remote_scope",
    [
        "this role is based in berlin",
        "full-time position in paris",
    ],
)
def test_apply_policy_marks_scope_negative_as_non_remote(remote_scope: str):
    job, reason = apply_policy(_job(remote_scope=remote_scope), source="employer_ing")

    assert reason is None
    assert job is not None
    assert job["_compliance"]["remote_model"] == RemoteClass.NON_REMOTE


def test_apply_policy_marks_hard_geo_restrictions():
    job, reason = apply_policy(
        _job(remote_scope="", description="US applicants only for this role."),
        source="employer_ing",
    )

    assert job is not None
    assert reason == "geo_restriction_hard"
    assert job["_compliance"]["policy_reason"] == "geo_restriction_hard"
    assert job["_compliance"]["geo_class"] == GeoClass.NON_EU


def test_apply_policy_marks_plain_remote_scope_as_remote_only():
    job, reason = apply_policy(_job(remote_scope="Remote"), source="employer_ing")

    assert reason is None
    assert job is not None
    assert job["_compliance"]["remote_model"] == RemoteClass.REMOTE_ONLY


def test_apply_policy_marks_region_locked_scope():
    job, reason = apply_policy(
        _job(remote_scope="Remote - Europe"),
        source="employer_ing",
    )

    assert reason is None
    assert job is not None
    assert job["_compliance"]["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED


def test_apply_policy_marks_title_negative_as_non_remote():
    job, reason = apply_policy(
        _job(remote_scope="Netherlands", title="Fulfilment Operations Associate | Netherlands, On-site"),
        source="employer_ing",
    )
    assert job["_compliance"]["remote_model"] == RemoteClass.NON_REMOTE


def test_apply_policy_remote_in_title_and_hybrid_in_desc_is_non_remote():
    job, reason = apply_policy(
        _job(remote_scope="", title="Data Engineer - Remote", description="Hybrid model, 3 days in office"),
        source="employer_ing",
    )
    assert job["_compliance"]["remote_model"] == RemoteClass.NON_REMOTE


def test_apply_policy_marks_eligible_to_work_in_us_as_hard_geo():
    job, reason = apply_policy(
        _job(remote_scope="", description="You must be eligible to work in the united states to apply."),
        source="employer_ing",
    )
    assert reason == "geo_restriction_hard"


def test_apply_policy_marks_home_based_scope_as_remote_only():
    job, reason = apply_policy(
        _job(remote_scope="home based"),
        source="employer_ing",
    )

    assert reason is None
    assert job is not None
    assert job["_compliance"]["remote_model"] == RemoteClass.REMOTE_ONLY


def test_apply_policy_marks_home_based_scope_as_region_locked():
    job, reason = apply_policy(
        _job(remote_scope="home based - emea"),
        source="employer_ing",
    )

    assert reason is None
    assert job is not None
    assert job["_compliance"]["remote_model"] == RemoteClass.REMOTE_REGION_LOCKED
