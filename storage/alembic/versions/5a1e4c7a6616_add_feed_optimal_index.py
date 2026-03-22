"""add feed optimal index

Revision ID: 5a1e4c7a6616
Revises: b2c3d4e5f6a1
Create Date: 2026-03-22 17:28:30.577417+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5a1e4c7a6616"
down_revision = "b2c3d4e5f6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Zakończenie domyślnej transakcji i przejście w tryb AUTOCOMMIT
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(
        sa.text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_feed_optimal ON jobs (status, compliance_score, first_seen_at DESC);"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_feed_optimal;"))
