from sqlalchemy import text
from sqlalchemy.engine import Connection


def insert_job_snapshot(
    conn: Connection,
    job_id: str,
    job_fingerprint: str,
    title: str | None = None,
    company_name: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    salary_currency: str | None = None,
    remote_class: str | None = None,
    geo_class: str | None = None,
) -> int:
    """
    Wstawia nowy zrzut historii ogłoszenia do tabeli job_snapshots.
    Zaprojektowane w celu śledzenia zmian tytułów oraz widełek wynagrodzeń w czasie.
    """
    stmt = text("""
        INSERT INTO job_snapshots (
            job_id,
            job_fingerprint,
            title,
            company_name,
            salary_min,
            salary_max,
            salary_currency,
            remote_class,
            geo_class,
            captured_at
        ) VALUES (
            :job_id,
            :job_fingerprint,
            :title,
            :company_name,
            :salary_min,
            :salary_max,
            :salary_currency,
            :remote_class,
            :geo_class,
            NOW()
        )
        RETURNING snapshot_id;
    """)

    result = conn.execute(stmt, dict(
        job_id=job_id,
        job_fingerprint=job_fingerprint,
        title=title,
        company_name=company_name,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        remote_class=remote_class,
        geo_class=geo_class,
    ))
    row = result.fetchone()
    return row[0] if row else 0