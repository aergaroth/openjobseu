from sqlalchemy import text
from storage.db_engine import get_engine

def get_companies_paginated(
    q: str | None = None,
    limit: int = 40,
    offset: int = 0
) -> tuple[list[dict], int]:
    engine = get_engine()
    
    # Publiczny endpoint udostępnia tylko aktywne firmy
    where_clauses = ["is_active = TRUE"]
    params = {"limit": limit, "offset": offset}
    order_by_sql = "signal_score DESC, created_at DESC"

    if q:
        where_clauses.append("(legal_name ILIKE :q_like OR brand_name ILIKE :q_like)")
        params["q_like"] = f"%{q}%"
        params["q_exact"] = q
        order_by_sql = "LEAST(legal_name <-> :q_exact, brand_name <-> :q_exact) ASC, signal_score DESC"

    where_sql = "WHERE " + " AND ".join(where_clauses)
    
    with engine.connect() as conn:
        total_query = f"SELECT COUNT(*) FROM companies {where_sql}"
        total = conn.execute(text(total_query), params).scalar()
        
        query = f"""
            SELECT 
                company_id, legal_name, brand_name, hq_country, remote_posture,
                approved_jobs_count, total_jobs_count
            FROM companies 
            {where_sql}
            ORDER BY {order_by_sql}
            LIMIT :limit OFFSET :offset
        """
        rows = conn.execute(text(query), params).mappings().all()

    return [dict(r, company_id=str(r["company_id"])) for r in rows], total or 0