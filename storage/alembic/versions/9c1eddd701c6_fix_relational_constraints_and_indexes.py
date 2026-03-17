"""fix relational constraints and indexes

Revision ID: 9c1eddd701c6
Revises: 09fad31be552
Create Date: 2026-03-17 19:41:21.482385+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c1eddd701c6'
down_revision = '09fad31be552'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Czyszczenie osieroconych rekordów (wymagane przed założeniem rygorystycznych kluczy obcych)
    op.execute("DELETE FROM salary_parsing_cases WHERE job_id NOT IN (SELECT job_id FROM jobs);")
    op.execute("DELETE FROM job_snapshots WHERE job_id NOT IN (SELECT job_id FROM jobs);")

    # 2. Naprawa tabeli salary_parsing_cases (Brakujący indeks i FK)
    op.execute("""
        ALTER TABLE salary_parsing_cases
        ADD CONSTRAINT fk_salary_cases_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_salary_cases_job_id
        ON salary_parsing_cases(job_id);
    """)

    # 3. Naprawa tabeli job_snapshots (Brakujący FK do kaskadowego usuwania)
    op.execute("""
        ALTER TABLE job_snapshots
        ADD CONSTRAINT fk_job_snapshots_job
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE;
    """)

    # 4. Usunięcie zduplikowanego indeksu z tabeli jobs (zostaje ten z 001)
    op.execute("DROP INDEX IF EXISTS idx_jobs_company;")

def downgrade() -> None:
    # Przywracanie struktury na wypadek wycofania migracji
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_id);")
    op.execute("ALTER TABLE job_snapshots DROP CONSTRAINT IF EXISTS fk_job_snapshots_job;")
    op.execute("DROP INDEX IF EXISTS idx_salary_cases_job_id;")
    op.execute("ALTER TABLE salary_parsing_cases DROP CONSTRAINT IF EXISTS fk_salary_cases_job;")