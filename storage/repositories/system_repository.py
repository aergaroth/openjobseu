from sqlalchemy import text
from storage.db_engine import get_engine

def get_system_metrics() -> dict:
    engine = get_engine()
    query = """
        SELECT 
            (SELECT COUNT(*) FROM jobs) as jobs_total,
            (SELECT COUNT(*) FROM jobs WHERE first_seen_at >= NOW() - INTERVAL '24 hours') as jobs_24h,
            (SELECT COUNT(*) FROM companies) as companies_total,
            (SELECT COUNT(*) FROM companies WHERE created_at >= NOW() - INTERVAL '24 hours') as companies_24h,
            (SELECT COUNT(*) FROM company_ats) as company_ats_total,
            (SELECT COUNT(*) FROM company_ats WHERE created_at >= NOW() - INTERVAL '24 hours') as company_ats_24h,
            (SELECT MAX(last_seen_at) FROM jobs) as last_tick_at
    """
    with engine.connect() as conn:
        row = conn.execute(text(query)).mappings().first()

    return {
        "jobs_total": row["jobs_total"] if row else 0,
        "jobs_24h": row["jobs_24h"] if row else 0,
        "companies_total": row["companies_total"] if row else 0,
        "companies_24h": row["companies_24h"] if row else 0,
        "company_ats_total": row["company_ats_total"] if row else 0,
        "company_ats_24h": row["company_ats_24h"] if row else 0,
        "last_tick_at": row["last_tick_at"].isoformat() if row and row["last_tick_at"] else None,
    }