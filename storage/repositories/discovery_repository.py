import uuid
from sqlalchemy import text
from sqlalchemy.engine import Connection
from storage.db_engine import get_engine

engine = get_engine()


def insert_source_company(conn: Connection, name: str, careers_url: str | None) -> bool:
    stmt = text("""
        INSERT INTO companies (
            company_id,
            brand_name,
            legal_name,
            hq_country,
            eu_entity_verified,
            remote_posture,
            careers_url,
            is_active,
            bootstrap,
            created_at,
            updated_at
        )
        VALUES (
            :uid, :name, :name, 'ZZ', false, 'UNKNOWN', :careers_url, true, true, NOW(), NOW()
        )
        ON CONFLICT DO NOTHING
        RETURNING company_id
    """)
    result = conn.execute(stmt, {
        "uid": uuid.uuid4(),
        "name": name,
        "careers_url": careers_url,
    })
    return result.fetchone() is not None


def load_discovery_companies(conn: Connection, phase: str, limit: int = 50) -> list[dict]:
    column = "careers_last_checked_at" if phase == "careers" else "ats_guess_last_checked_at"
    query = f"""
        SELECT
            c.company_id,
            c.legal_name,
            c.brand_name,
            c.careers_url
        FROM companies c
        WHERE c.is_active = TRUE
          AND c.ats_provider IS NULL
          AND c.careers_url IS NOT NULL
        ORDER BY c.{column} NULLS FIRST
        LIMIT :limit
    """
    rows = conn.execute(text(query), {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def update_discovery_last_checked_at(conn: Connection, company_id: str, phase: str) -> None:
    column = "careers_last_checked_at" if phase == "careers" else "ats_guess_last_checked_at"
    conn.execute(
        text(f"""
            UPDATE companies
            SET {column} = NOW()
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


def get_discovered_company_ats(limit: int = 100) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    c.legal_name AS company_name,
                    ca.provider,
                    ca.ats_slug,
                    ca.careers_url,
                    ca.created_at
                FROM company_ats ca
                JOIN companies c
                    ON ca.company_id = c.company_id
                ORDER BY ca.created_at DESC
                LIMIT :limit
            """),
            {"limit": int(limit)},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_discovery_candidates(limit: int = 50) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    company_id,
                    legal_name,
                    careers_url,
                    careers_last_checked_at,
                    ats_guess_last_checked_at
                FROM companies
                WHERE ats_provider IS NULL
                  AND careers_url IS NOT NULL
                ORDER BY careers_last_checked_at NULLS FIRST, ats_guess_last_checked_at NULLS FIRST
                LIMIT :limit
            """),
            {"limit": int(limit)},
        ).mappings().all()

    return [dict(row) for row in rows]