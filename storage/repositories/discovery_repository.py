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


def check_ats_exists(conn: Connection, provider: str, ats_slug: str) -> bool:
    exists = conn.execute(
        text("SELECT 1 FROM company_ats WHERE provider = :provider AND ats_slug = :slug LIMIT 1"),
        {"provider": provider, "slug": ats_slug}
    ).fetchone()
    return bool(exists)


def get_or_create_placeholder_company(conn: Connection, name: str) -> str:
    existing_company = conn.execute(
        text("SELECT company_id FROM companies WHERE lower(legal_name) = lower(:name) LIMIT 1"),
        {"name": name}
    ).fetchone()

    if existing_company:
        return str(existing_company[0])

    company_id = str(uuid.uuid4())
    conn.execute(
        text("""
            INSERT INTO companies (
                company_id, brand_name, legal_name, hq_country, eu_entity_verified,
                remote_posture, is_active, bootstrap, created_at, updated_at
            )
            VALUES (
                :uid, :name, :name, 'ZZ', false, 'UNKNOWN', true, true, NOW(), NOW()
            )
        """),
        {"uid": company_id, "name": name}
    )
    return company_id


def insert_discovered_company_ats(
    conn: Connection,
    *,
    company_id: str,
    provider: str,
    ats_slug: str,
    careers_url: str | None = None,
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


def get_discovered_company_ats(q: str | None = None, limit: int = 100) -> list[dict]:
    where_clause = ""
    params = {"limit": int(limit)}
    order_by_sql = "ca.created_at DESC"

    if q:
        where_clause = "WHERE c.legal_name ILIKE :q_like OR c.brand_name ILIKE :q_like"
        params["q_like"] = f"%{q}%"
        params["q_exact"] = q
        order_by_sql = "LEAST(c.legal_name <-> :q_exact, c.brand_name <-> :q_exact) ASC, ca.created_at DESC"

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT
                    c.legal_name AS company_name,
                    ca.provider,
                    ca.ats_slug,
                    ca.careers_url,
                    ca.created_at
                FROM company_ats ca
                JOIN companies c
                    ON ca.company_id = c.company_id
                {where_clause}
                ORDER BY {order_by_sql}
                LIMIT :limit
            """),
            params,
        ).mappings().all()

    return [dict(row) for row in rows]


def get_discovery_candidates(q: str | None = None, limit: int = 50) -> list[dict]:
    where_sql = "WHERE ats_provider IS NULL AND careers_url IS NOT NULL"
    order_by_sql = "careers_last_checked_at NULLS FIRST, ats_guess_last_checked_at NULLS FIRST"
    params = {"limit": int(limit)}

    if q:
        where_sql += " AND (legal_name ILIKE :q_like OR brand_name ILIKE :q_like)"
        params["q_like"] = f"%{q}%"
        params["q_exact"] = q
        order_by_sql = f"LEAST(legal_name <-> :q_exact, brand_name <-> :q_exact) ASC, {order_by_sql}"

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT
                    company_id,
                    legal_name,
                    careers_url,
                    careers_last_checked_at,
                    ats_guess_last_checked_at
                FROM companies
                {where_sql}
                ORDER BY {order_by_sql}
                LIMIT :limit
            """),
            params,
        ).mappings().all()

    return [dict(row) for row in rows]


def get_existing_brand_names(conn: Connection) -> set[str]:
    """Fetches a set of all non-null brand names in lowercase."""
    rows = conn.execute(
        text("SELECT brand_name FROM companies WHERE brand_name IS NOT NULL")
    ).fetchall()
    return {row[0].lower() for row in rows}


def insert_discovered_slugs(conn: Connection, slugs: list[dict]):
    """Bulk inserts newly discovered slugs into the discovered_slugs table."""
    if not slugs:
        return

    stmt = text("""
        INSERT INTO discovered_slugs (provider, slug, discovery_source)
        VALUES (:provider, :slug, :discovery_source)
        ON CONFLICT (provider, slug) DO NOTHING
    """)
    conn.execute(stmt, slugs)