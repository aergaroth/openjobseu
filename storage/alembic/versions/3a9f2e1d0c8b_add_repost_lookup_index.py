"""add repost lookup index

Revision ID: 3a9f2e1d0c8b
Revises: 5a1e4c7a6616
Create Date: 2026-04-02 12:00:00.000000+00:00

Supports the self-join in mark_reposts_due_to_lifecycle() and the analogous
query in audit_repository.get_repost_candidates():

  JOIN jobs prev ON cur.job_fingerprint = prev.job_fingerprint
                AND cur.company_name    = prev.company_name
                AND cur.title           = prev.title
                AND cur.first_seen_at   > prev.last_seen_at
                AND <time window>

Without this index both sides of the self-join do sequential scans as the
`jobs` table grows.
"""

from alembic import op
import sqlalchemy as sa

revision = "3a9f2e1d0c8b"
down_revision = "5a1e4c7a6616"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(
        sa.text("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_repost_lookup
            ON jobs (job_fingerprint, company_name, title, last_seen_at DESC)
        """)
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_repost_lookup"))
