"""Add salary_count to market_daily_stats_segments

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-04-22 00:00:00.000000+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a4b5c6d7e8"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_daily_stats_segments",
        sa.Column("salary_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("market_daily_stats_segments", "salary_count")
