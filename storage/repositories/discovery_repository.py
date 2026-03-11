from sqlalchemy import text
from sqlalchemy.engine import Connection


def load_discovery_companies(conn: Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        text("""
            SELECT
                c.company_id,
                c.legal_name,
                c.careers_url
            FROM companies c
            WHERE c.bootstrap = FALSE
              AND c.is_active = TRUE
              AND c.ats_provider IS NULL
              AND c.careers_url IS NOT NULL
            ORDER BY c.discovery_last_checked_at NULLS FIRST
            LIMIT :limit
        """),
        {"limit": limit},
    ).mappings().all()

    return [dict(row) for row in rows]


def update_discovery_last_checked_at(conn: Connection, company_id: str) -> None:
    conn.execute(
        text("""
            UPDATE companies
            SET discovery_last_checked_at = NOW()
            WHERE company_id = :company_id
        """),
        {"company_id": company_id},
    )


def insert_discovered_company_ats(
    conn: Connection,
    *,
    company_id: str,
    provider: str,
    ats_slug: str,
    careers_url: str,
) -> bool:
    result = conn.execute(
        text("""
            INSERT INTO company_ats (company_id, provider, ats_slug, careers_url)
            VALUES (:company_id, :provider, :ats_slug, :careers_url)
            ON CONFLICT DO NOTHING
            RETURNING company_ats_id
        """),
        {
            "company_id": company_id,
            "provider": provider,
            "ats_slug": ats_slug,
            "careers_url": careers_url,
        },
    )
    return bool(result.fetchone())