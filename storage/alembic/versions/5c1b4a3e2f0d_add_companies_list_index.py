"""add companies list index

Revision ID: 5c1b4a3e2f0d
Revises: 4b0a3f2e1d9c
Create Date: 2026-04-02 12:02:00.000000+00:00

Supports the common query pattern for company listings:
  WHERE is_active = TRUE
  ORDER BY signal_score DESC, created_at DESC

Without this index the planner falls back to a sequential scan when ordering
by signal_score on large company sets.
"""

from alembic import op
import sqlalchemy as sa

revision = "5c1b4a3e2f0d"
down_revision = "4b0a3f2e1d9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(
        sa.text("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_active_score
            ON companies (is_active, signal_score DESC, created_at DESC)
        """)
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_companies_active_score"))
