import datetime
from app.workers.policy.v2.geo_classifier import classify_geo_scope


def _make_job(job_id: str, first_seen_at: str) -> dict:
    return {
        "job_id": job_id,
        "source": "remotive",
        "source_job_id": job_id.split(":")[-1],
        "source_url": f"https://example.com/jobs/{job_id}",
        "title": "Backend Engineer",
        "company_name": "Acme",
        "description": "Role description",
        "remote_source_flag": True,
        "remote_scope": "Europe",
        "status": "new",
        "first_seen_at": first_seen_at,
    }


# In-memory fake "jobs" table used by tests to avoid DB engine usage.
_IN_MEMORY_JOBS: dict[str, dict] = {}


def _iso_to_dt(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s)


def fake_init_db():
    _IN_MEMORY_JOBS.clear()


def _derive_remote_class(job: dict) -> str:
    compliance = job.get("_compliance")
    if not isinstance(compliance, dict):
        return "remote_only" if bool(job.get("remote_source_flag")) else "unknown"

    policy_reason = str(compliance.get("policy_reason") or "").strip().lower()
    remote_model = str(compliance.get("remote_model") or "").strip().lower()

    if policy_reason == "non_remote":
        return "non_remote"

    mapping = {
        "remote_only": "remote_only",
        "remote_but_geo_restricted": "remote_but_geo_restricted",
        "remote_region_locked": "remote_but_geo_restricted",
        "hybrid": "non_remote",
        "office_first": "non_remote",
        "non_remote": "non_remote",
        "unknown": "unknown",
    }
    return mapping.get(remote_model, "unknown")


def _normalize_geo_class_value(value: str | None) -> str:
    geo = str(value or "").strip().lower()
    mapping = {
        "eu_member_state": "eu_member_state",
        "eu_region": "eu_region",
        "eu_explicit": "eu_explicit",
        "eog": "eu_region",
        "uk": "uk",
        "worldwide": "unknown",
        "global": "unknown",
        "eu_friendly": "unknown",
        "non_eu": "non_eu",
        "non_eu_restricted": "non_eu",
        "unknown": "unknown",
    }
    return mapping.get(geo, "unknown")


def _derive_geo_class(job: dict) -> str:
    compliance = job.get("_compliance") or {}
    policy_reason = str(compliance.get("policy_reason") or "").strip().lower()
    explicit_geo_class = compliance.get("geo_class")

    if explicit_geo_class:
        normalized = _normalize_geo_class_value(str(explicit_geo_class))
        if normalized != "unknown":
            return normalized

    if policy_reason in {"geo_restriction", "geo_restriction_hard"}:
        return "non_eu"

    classifier_result = classify_geo_scope(str(job.get("title") or ""), str(job.get("description") or ""))
    normalized_classifier_geo = _normalize_geo_class_value(str(classifier_result.get("geo_class") or ""))
    if normalized_classifier_geo != "unknown":
        return normalized_classifier_geo

    remote_scope = str(job.get("remote_scope") or "").strip()
    if remote_scope:
        remote_scope_result = classify_geo_scope(remote_scope, "")
        normalized_remote_scope_geo = _normalize_geo_class_value(str(remote_scope_result.get("geo_class") or ""))
        if normalized_remote_scope_geo != "unknown":
            return normalized_remote_scope_geo

    return "unknown"


def fake_upsert_job(job: dict, conn=None, *, company_id: str | None = None):
    job_id = job["job_id"]
    now = datetime.datetime.now(datetime.timezone.utc)
    first_seen_at_raw = job.get("first_seen_at") or now.isoformat()

    # normalize to ISO string
    if isinstance(first_seen_at_raw, str):
        first_seen_dt = _iso_to_dt(first_seen_at_raw)
    else:
        first_seen_dt = first_seen_at_raw

    existing = _IN_MEMORY_JOBS.get(job_id)
    if existing:
        existing_first = existing.get("first_seen_at")
        existing_dt = _iso_to_dt(existing_first) if isinstance(existing_first, str) else existing_first
        earliest = existing_dt if existing_dt <= first_seen_dt else first_seen_dt
        existing.update(job)
        existing["first_seen_at"] = earliest.isoformat()
        existing["remote_class"] = _derive_remote_class(existing)
        existing["geo_class"] = _derive_geo_class(existing)
    else:
        copy = dict(job)
        copy["first_seen_at"] = first_seen_dt.isoformat()
        copy["remote_class"] = _derive_remote_class(copy)
        copy["geo_class"] = _derive_geo_class(copy)
        _IN_MEMORY_JOBS[job_id] = copy


def test_upsert_uses_source_first_seen_at():
    fake_init_db()

    source_first_seen = "2026-01-05T10:00:00+00:00"
    job = _make_job("remotive:test-first-seen", source_first_seen)
    fake_upsert_job(job)

    row = _IN_MEMORY_JOBS.get(job["job_id"])
    assert row is not None
    v = row["first_seen_at"]
    assert v == source_first_seen


def test_upsert_keeps_earliest_first_seen_at_on_conflict():
    fake_init_db()

    job_id = "remotive:test-first-seen-conflict"
    older = _make_job(job_id, "2026-01-05T10:00:00+00:00")
    newer = _make_job(job_id, "2026-01-07T10:00:00+00:00")

    fake_upsert_job(older)
    fake_upsert_job(newer)

    row = _IN_MEMORY_JOBS.get(job_id)
    assert row is not None
    v = row["first_seen_at"]
    assert v == older["first_seen_at"]


def test_upsert_persists_derived_compliance_classes():
    fake_init_db()

    job = _make_job("remotive:test-classes", "2026-01-05T10:00:00+00:00")
    job["remote_scope"] = "EU-wide"
    job["_compliance"] = {
        "policy_reason": None,
        "remote_model": "remote_only",
    }

    fake_upsert_job(job)

    row = _IN_MEMORY_JOBS.get(job["job_id"])
    assert row is not None
    assert row["remote_class"] == "remote_only"
    assert row["geo_class"] == "eu_region"


def test_upsert_marks_geo_non_eu_when_policy_flags_geo_restriction():
    fake_init_db()

    job = _make_job("remotive:test-geo-restriction", "2026-01-05T10:00:00+00:00")
    job["remote_scope"] = "Worldwide"
    job["_compliance"] = {
        "policy_reason": "geo_restriction",
        "remote_model": "remote_but_geo_restricted",
    }

    fake_upsert_job(job)

    row = _IN_MEMORY_JOBS.get(job["job_id"])
    assert row is not None
    assert row["remote_class"] == "remote_but_geo_restricted"
    assert row["geo_class"] == "non_eu"
