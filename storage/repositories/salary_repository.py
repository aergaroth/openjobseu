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
