"""Create discovered_slugs table

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 00:00:00.000000+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovered_slugs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("discovery_source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("provider", "slug", name="uq_discovered_slugs_provider_slug"),
    )
    op.create_index("idx_discovered_slugs_status", "discovered_slugs", ["status"])


def downgrade() -> None:
    op.drop_table("discovered_slugs")
