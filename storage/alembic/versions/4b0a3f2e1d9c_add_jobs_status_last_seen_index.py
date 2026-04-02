"""add jobs status last_seen_at index

Revision ID: 4b0a3f2e1d9c
Revises: 3a9f2e1d0c8b
Create Date: 2026-04-02 12:01:00.000000+00:00

Supports list/audit queries that filter by status and sort by last_seen_at DESC.
The existing idx_jobs_feed_optimal covers (status, compliance_score, first_seen_at DESC)
but does not help when sorting by last_seen_at.
"""

from alembic import op
import sqlalchemy as sa

revision = "4b0a3f2e1d9c"
down_revision = "3a9f2e1d0c8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(
        sa.text("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status_last_seen
            ON jobs (status, last_seen_at DESC)
        """)
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_status_last_seen"))
