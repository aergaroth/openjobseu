"""Rename salary_parsing_cases columns

Revision ID: d4e5f6a1b2c3
Revises: 9c1eddd701c6
Create Date: 2026-03-18 22:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a1b2c3'
down_revision = '9c1eddd701c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('salary_parsing_cases', 'parser_min', new_column_name='extracted_min', existing_type=sa.Integer())
    op.alter_column('salary_parsing_cases', 'parser_max', new_column_name='extracted_max', existing_type=sa.Integer())
    op.alter_column('salary_parsing_cases', 'parser_currency', new_column_name='extracted_currency', existing_type=sa.String())


def downgrade() -> None:
    op.alter_column('salary_parsing_cases', 'extracted_min', new_column_name='parser_min', existing_type=sa.Integer())
    op.alter_column('salary_parsing_cases', 'extracted_max', new_column_name='parser_max', existing_type=sa.Integer())
    op.alter_column('salary_parsing_cases', 'extracted_currency', new_column_name='parser_currency', existing_type=sa.String())
