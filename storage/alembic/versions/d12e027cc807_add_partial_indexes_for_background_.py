"""add partial indexes for background workers

Revision ID: d12e027cc807
Revises: 42755286f279
Create Date: 2026-03-17 19:07:17.299754+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd12e027cc807'
down_revision = '42755286f279'
branch_labels = None
depends_on = None


from alembic import op

def upgrade() -> None:
    # Zamknięcie domyślnego bloku transakcji wymuszonego przez alembic/env.py
    bind = op.get_bind()
    bind.commit()

    # Otwarcie połączenia z odpowiednim poziomem izolacji (wymagane dla CONCURRENTLY)
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    # 1. Złoty indeks dla modułu Availability
    conn.execute(sa.text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_availability_queue 
        ON jobs (last_verified_at ASC NULLS FIRST) 
        WHERE status IN ('active', 'stale');
    """))
    
    # 2. Mikro-kolejka dla systemu Compliance
    conn.execute(sa.text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_pending_compliance 
        ON jobs (last_seen_at DESC) 
        WHERE compliance_status IS NULL OR compliance_score IS NULL;
    """))
    
    # 3. Sterowanie Cyklem Życia (Lifecycle Transitions)
    conn.execute(sa.text("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_lifecycle_new_activation 
        ON jobs (first_seen_at) 
        WHERE status = 'new';
    """))

def downgrade() -> None:
    # W bezpiecznym świecie używamy również CONCURRENTLY do usuwania indeksów
    bind = op.get_bind()
    bind.commit()
    conn = bind.execution_options(isolation_level="AUTOCOMMIT")

    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_lifecycle_new_activation;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_pending_compliance;"))
    conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_availability_queue;"))
