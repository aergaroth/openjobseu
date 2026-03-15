"""add compliance classes to job snapshots

Revision ID: 42755286f279
Revises: 56f2bf3724cd
Create Date: 2026-03-15 22:42:22.975380+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '42755286f279'
down_revision = '56f2bf3724cd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE job_snapshots 
        ADD COLUMN IF NOT EXISTS remote_class TEXT,
        ADD COLUMN IF NOT EXISTS geo_class TEXT;
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE job_snapshots 
        DROP COLUMN IF EXISTS remote_class,
        DROP COLUMN IF EXISTS geo_class;
    """)
    
