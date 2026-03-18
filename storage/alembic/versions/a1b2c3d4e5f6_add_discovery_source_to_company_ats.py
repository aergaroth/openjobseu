"""Add discovery_source to company_ats

Revision ID: a1b2c3d4e5f6
Revises: d4e5f6a1b2c3
Create Date: 2026-03-18 23:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd4e5f6a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('company_ats', sa.Column('discovery_source', sa.String(), nullable=True))
    op.create_index('idx_company_ats_discovery_source', 'company_ats', ['discovery_source'])


def downgrade() -> None:
    op.drop_index('idx_company_ats_discovery_source', 'company_ats')
    op.drop_column('company_ats', 'discovery_source')
