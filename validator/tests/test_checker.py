from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from validator.checker import AvailabilityChecker


def make_job(**overrides):
    base = {
        "job_id": "123",
        "source": "example_source",
        "source_url": "https://example.com/job",
        "status": "active",
        "last_verified_at": None,
        "verification_failures": 0,
    }
    base.update(overrides)
    return base


@patch("validator.checker.requests.head")
def test_job_becomes_active_on_200(mock_head):
    mock_head.return_value = Mock(status_code=200)

    checker = AvailabilityChecker()
    job = make_job(last_verified_at=None)

    updated = checker.check(job)

    assert updated["status"] == "active"
    assert updated["verification_failures"] == 0


@patch("validator.checker.requests.head")
def test_job_becomes_expired_on_404(mock_head):
    mock_head.return_value = Mock(status_code=404)

    checker = AvailabilityChecker()
    job = make_job(last_verified_at=None)

    updated = checker.check(job)

    assert updated["status"] == "expired"


@patch("validator.checker.requests.head", side_effect=Exception)
def test_job_becomes_unreachable_on_exception(mock_head):
    checker = AvailabilityChecker()
    job = make_job(last_verified_at=None)

    updated = checker.check(job)

    assert updated["status"] == "unreachable"
    assert updated["verification_failures"] == 1


def test_job_becomes_stale_when_ttl_exceeded():
    checker = AvailabilityChecker()
    old_date = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()

    job = make_job(last_verified_at=old_date)

    updated = checker.check(job)

    assert updated["status"] == "stale"
