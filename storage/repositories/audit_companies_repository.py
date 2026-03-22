from sqlalchemy import text
from storage.db_engine import get_engine


def get_audit_companies_list(
    q: str | None = None,
    ats_provider: str | None = None,
    is_active: bool | None = None,
    min_score: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    engine = get_engine()
    where_clauses, params = [], {"limit": limit, "offset": offset}
    order_by_sql = "signal_score DESC, created_at DESC"

    if q:
        where_clauses.append("(legal_name ILIKE :q_like OR brand_name ILIKE :q_like)")
        params["q_like"], params["q_exact"] = f"%{q}%", q
        order_by_sql = "LEAST(legal_name <-> :q_exact, brand_name <-> :q_exact) ASC, signal_score DESC"
    if ats_provider:
        where_clauses.append("ats_provider = :ats_provider")
        params["ats_provider"] = ats_provider
    if is_active is not None:
        where_clauses.append("is_active = :is_active")
        params["is_active"] = is_active
    if min_score is not None:
        where_clauses.append("signal_score >= :min_score")
        params["min_score"] = min_score

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    with engine.connect() as conn:
        total_query = (
            f"SELECT COUNT(*) FROM companies {where_sql}"
            if where_sql
            else "SELECT GREATEST(0, CAST(reltuples AS BIGINT)) FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = 'public' AND c.relname = 'companies'"
        )
        total = conn.execute(text(total_query), params).scalar()

        query = f"SELECT company_id, legal_name, brand_name, hq_country, eu_entity_verified, remote_posture, ats_provider, ats_slug, signal_score, approved_jobs_count, rejected_jobs_count, total_jobs_count, last_active_job_at, is_active, created_at FROM companies {where_sql} ORDER BY {order_by_sql} LIMIT :limit OFFSET :offset"
        rows = conn.execute(text(query), params).mappings().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [dict(r) for r in rows],
    }
