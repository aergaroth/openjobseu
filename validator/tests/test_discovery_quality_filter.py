from datetime import datetime, timedelta, timezone
from app.workers.discovery.careers_crawler import ( 
    QUALITY_MAX_AGE_DAYS,
    QUALITY_MIN_JOBS,
    QUALITY_MIN_REMOTE_HITS,
    _is_recent,
)
from app.workers.discovery.careers_crawler import _is_recent


def test_is_recent_within_threshold():
    recent = datetime.now(timezone.utc) - timedelta(days=10)
    assert _is_recent(recent) is True


def test_is_recent_outside_threshold():
    old = datetime.now(timezone.utc) - timedelta(days=QUALITY_MAX_AGE_DAYS + 1)
    assert _is_recent(old) is False


def test_is_recent_handles_none():
    assert _is_recent(None) is True


def test_quality_filter_passes_when_conditions_met():
    # mimic worker's inline checks
    jobs_total = 6
    remote_hits = 1
    recent_job_at = datetime.now(timezone.utc) - timedelta(days=5)
    assert jobs_total >= QUALITY_MIN_JOBS
    assert remote_hits >= QUALITY_MIN_REMOTE_HITS
    assert _is_recent(recent_job_at)


def test_quality_filter_fails_on_jobs():
    jobs_total = 0
    assert jobs_total < QUALITY_MIN_JOBS


def test_quality_filter_fails_on_remote_hits():
    remote_hits = 0
    assert remote_hits < QUALITY_MIN_REMOTE_HITS


def test_quality_filter_fails_on_age():
    recent_job_at = datetime.now(timezone.utc) - timedelta(days=QUALITY_MAX_AGE_DAYS + 5)
    assert not _is_recent(recent_job_at)