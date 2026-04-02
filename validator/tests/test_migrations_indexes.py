"""Smoke tests confirming that the expected performance indexes exist in the DB schema.

These run against the test database (migrated to head by conftest.py) and simply
verify that the indexes were created — they do not test query plans or CONCURRENTLY
semantics, which are production-only concerns.
"""

import pytest
from sqlalchemy import text
from storage.db_engine import get_engine


@pytest.mark.parametrize(
    "indexname",
    [
        # Lifecycle / repost self-join
        "idx_jobs_repost_lookup",
        # List API — status + last_seen_at
        "idx_jobs_status_last_seen",
        # Companies list — active + score
        "idx_companies_active_score",
        # Pre-existing indexes that must not have been dropped
        "idx_jobs_feed_optimal",
        "idx_jobs_availability_queue",
        "idx_jobs_pending_compliance",
    ],
)
def test_index_exists(indexname):
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": indexname},
        ).scalar()
    assert result == 1, f"Expected index '{indexname}' to exist in pg_indexes"
