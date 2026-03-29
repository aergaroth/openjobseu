from sqlalchemy import text
from sqlalchemy.engine import Connection


def insert_salary_parsing_case(
    conn: Connection,
    job_id: str,
    salary_raw: str | None = None,
    description_fragment: str | None = None,
    parser_confidence: float | None = None,
    extracted_min: int | None = None,
    extracted_max: int | None = None,
    extracted_currency: str | None = None,
) -> None:
    """
    Zapisuje "trudne przypadki" ekstrakcji wynagrodzenia z tekstu do analizy.
    Odkłada dane wyciągnięte przez regexy/NLP do tabeli salary_parsing_cases
    ze statusem 'needs_review', co ułatwia douczanie algorytmów.
    """
    stmt = text("""
        INSERT INTO salary_parsing_cases (
            job_id,
            salary_raw,
            description_fragment,
            parser_confidence,
            extracted_min,
            extracted_max,
            extracted_currency,
            status,
            created_at
        ) VALUES (
            :job_id,
            :salary_raw,
            :description_fragment,
            :parser_confidence,
            :extracted_min,
            :extracted_max,
            :extracted_currency,
            'needs_review',
            NOW()
        )
        ON CONFLICT DO NOTHING
    """)

    conn.execute(
        stmt,
        dict(
            job_id=job_id,
            salary_raw=salary_raw,
            description_fragment=description_fragment,
            parser_confidence=parser_confidence,
            extracted_min=extracted_min,
            extracted_max=extracted_max,
            extracted_currency=extracted_currency,
        ),
    )


def insert_salary_parsing_cases(conn: Connection, cases: list[dict]) -> None:
    """
    Wersja bulk (wsadowa) dla zapisu trudnych przypadków ekstrakcji wynagrodzenia.
    """
    if not cases:
        return

    stmt = text("""
        INSERT INTO salary_parsing_cases (
            job_id,
            salary_raw,
            description_fragment,
            parser_confidence,
            extracted_min,
            extracted_max,
            extracted_currency,
            status,
            created_at
        ) VALUES (
            :job_id,
            :salary_raw,
            :description_fragment,
            :parser_confidence,
            :extracted_min,
            :extracted_max,
            :extracted_currency,
            'needs_review',
            NOW()
        )
        ON CONFLICT DO NOTHING
    """)

    conn.execute(stmt, cases)


def get_jobs_with_missing_salary(conn: Connection, limit: int) -> list[dict]:
    """
    Fetches jobs that are missing salary data (both min and max are NULL).
    """
    query = text("""
        SELECT
            job_id, title, description
        FROM jobs
        WHERE salary_min IS NULL AND salary_max IS NULL
        ORDER BY COALESCE(last_seen_at, '1970-01-01T00:00:00+00:00') DESC
        LIMIT :limit
    """)
    rows = conn.execute(query, {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def update_job_salaries_bulk(conn: Connection, job_updates: list[dict]) -> None:
    """
    Bulk updates jobs with new salary data from the backfill process.
    """
    if not job_updates:
        return

    conn.execute(
        text("""
            UPDATE jobs
            SET
                salary_min = :salary_min,
                salary_max = :salary_max,
                salary_currency = :salary_currency,
                salary_period = :salary_period,
                salary_source = :salary_source,
                salary_min_eur = :salary_min_eur,
                salary_max_eur = :salary_max_eur,
                updated_at = :updated_at
            WHERE job_id = :job_id
        """),
        job_updates,
    )
