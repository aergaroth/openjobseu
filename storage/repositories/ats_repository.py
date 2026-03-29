from sqlalchemy import text
from sqlalchemy.engine import Connection


def get_ats_integration_by_id(conn: Connection, company_ats_id: str) -> dict | None:
    """Load a single ATS integration by its ID."""
    row = (
        conn.execute(
            text("""
            SELECT
                ca.company_ats_id,
                ca.company_id,
                c.legal_name,
                ca.provider,
                ca.provider AS ats_provider,
                ca.ats_slug,
                ca.ats_api_url,
                ca.careers_url,
                ca.last_sync_at
            FROM company_ats ca
            JOIN companies c ON c.company_id = ca.company_id
            WHERE ca.company_ats_id = :company_ats_id
        """),
            {"company_ats_id": company_ats_id},
        )
        .mappings()
        .fetchone()
    )
    return dict(row) if row else None


def load_active_ats_companies(conn: Connection, limit: int = 100) -> list[dict]:
    """Load active ATS configurations for companies."""
    rows = (
        conn.execute(
            text("""
            SELECT
                ca.company_ats_id,
                ca.company_id,
                c.legal_name,
                ca.provider,
                ca.provider AS ats_provider,
                ca.ats_slug,
                ca.ats_api_url,
                ca.careers_url,
                ca.last_sync_at
            FROM company_ats ca
            JOIN companies c ON c.company_id = ca.company_id
            WHERE c.is_active = TRUE
              AND ca.is_active = TRUE
              AND ca.provider IS NOT NULL
              AND ca.ats_slug IS NOT NULL
            ORDER BY ca.updated_at ASC NULLS FIRST
            LIMIT :limit
        """),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in rows]


def mark_ats_synced(conn: Connection, company_ats_id: str | None, success: bool = True) -> None:
    """Update the last sync timestamp for an ATS configuration."""
    if not company_ats_id:
        return

    if success:
        conn.execute(
            text("""
                UPDATE company_ats
                SET
                    last_sync_at = NOW(),
                    updated_at = NOW()
                WHERE company_ats_id = :company_ats_id
            """),
            {"company_ats_id": str(company_ats_id)},
        )
    else:
        conn.execute(
            text("""
                UPDATE company_ats
                SET updated_at = NOW()
                WHERE company_ats_id = :company_ats_id
            """),
            {"company_ats_id": str(company_ats_id)},
        )


def deactivate_ats_integration(conn: Connection, company_ats_id: str) -> None:
    """Mark an ATS integration as inactive."""
    conn.execute(
        text("""
            UPDATE company_ats
            SET
                is_active = FALSE,
                updated_at = NOW()
            WHERE company_ats_id = :company_ats_id
        """),
        {"company_ats_id": str(company_ats_id)},
    )
