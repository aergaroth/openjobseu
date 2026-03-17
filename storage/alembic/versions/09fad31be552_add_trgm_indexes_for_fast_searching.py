"""add trgm indexes for fast searching

Revision ID: 09fad31be552
Revises: d12e027cc807
Create Date: 2026-03-17 19:37:46.100653+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09fad31be552'
down_revision = 'd12e027cc807'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    # Bezpieczne włączenie modułu trigramów (zabezpieczenie przed brakiem uprawnień w Cloud SQL)
    has_trgm = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).scalar()
    if not has_trgm:
        try:
            conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        except Exception as e:
            raise RuntimeError(
                "\n"
                "========================================================================\n"
                "BRAK UPRAWNIEŃ DO INSTALACJI ROZSZERZENIA 'pg_trgm' W BAZIE DANYCH!\n"
                "Zaloguj się do konsoli swojego dostawcy (np. Neon SQL Editor) jako\n"
                "właściciel bazy danych (admin) i wykonaj ręcznie komendę:\n\n"
                "CREATE EXTENSION IF NOT EXISTS pg_trgm;\n\n"
                "Po wykonaniu tej komendy ponów deployment (Cloud Run sam ruszy dalej).\n"
                "========================================================================"
            ) from e
    
    # Tworzenie wydajnych indeksów typu GIN dla wyszukiwarki API
    conn.execute(sa.text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_title_trgm ON jobs USING GIN (title gin_trgm_ops);"))
    conn.execute(sa.text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_company_name_trgm ON jobs USING GIN (company_name gin_trgm_ops);"))
    conn.execute(sa.text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_remote_scope_trgm ON jobs USING GIN (remote_scope gin_trgm_ops);"))
    
    # Indeksy GIN dla wyszukiwarki firm
    conn.execute(sa.text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_legal_name_trgm ON companies USING GIN (legal_name gin_trgm_ops);"))
    conn.execute(sa.text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_brand_name_trgm ON companies USING GIN (brand_name gin_trgm_ops);"))

def downgrade() -> None:
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_companies_brand_name_trgm;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_companies_legal_name_trgm;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_remote_scope_trgm;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_company_name_trgm;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_title_trgm;"))
    
    # Z reguły w downgradzie zostawia się rozszerzenie aktywne, ponieważ mogą z niego 
    # korzystać już inne, zewnątrznie nałożone indeksy. 
    # conn.execute(sa.text("DROP EXTENSION IF EXISTS pg_trgm;"))