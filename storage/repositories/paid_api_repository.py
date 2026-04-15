from datetime import date

from sqlalchemy import text

from storage.db_engine import get_engine

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


_PAID_JOB_SELECT = """
    SELECT
        job_id,
        source,
        source_url,
        title,
        company_name,
        remote_scope,
        status,
        remote_class,
        geo_class,
        compliance_status,
        compliance_score,
        job_quality_score AS quality_score,
        description,
        source_department,
        job_family,
        job_role,
        seniority,
        specialization,
        salary_min,
        salary_max,
        salary_currency,
        salary_period,
        salary_min_eur,
        salary_max_eur,
        first_seen_at,
        last_seen_at
    FROM jobs
"""


def _build_paid_jobs_where(
    *,
    status: str | None,
    q: str | None,
    company: str | None,
    title: str | None,
    source: str | None,
    remote_scope: str | None,
    remote_class: str | None,
    geo_class: str | None,
    compliance_status: str | None,
    min_compliance_score: int | None,
    max_compliance_score: int | None,
    job_family: str | None,
    seniority: str | None,
    specialization: str | None,
    first_seen_after: date | None,
    first_seen_before: date | None,
) -> tuple[str, dict]:
    clauses: list[str] = []
    params: dict = {}
    n = 0

    def _p(value) -> str:
        nonlocal n
        n += 1
        key = f"p{n}"
        params[key] = value
        return f":{key}"

    if status == "visible":
        clauses.append("status IN ('new', 'active')")
    elif status:
        clauses.append(f"status = {_p(status)}")

    if company:
        clauses.append(f"company_name ILIKE {_p('%' + company + '%')}")

    if title:
        clauses.append(f"title ILIKE {_p('%' + title + '%')}")

    if source:
        clauses.append(
            f"EXISTS (SELECT 1 FROM job_sources js_f WHERE js_f.job_id = jobs.job_id AND js_f.source = {_p(source)})"
        )

    if remote_scope:
        clauses.append(f"remote_scope = {_p(remote_scope)}")

    if remote_class:
        clauses.append(f"remote_class = {_p(remote_class)}")

    if geo_class:
        clauses.append(f"geo_class = {_p(geo_class)}")

    if compliance_status:
        clauses.append(f"compliance_status = {_p(compliance_status)}")

    if min_compliance_score is not None:
        if int(min_compliance_score) <= 0:
            clauses.append(f"COALESCE(compliance_score, 0) >= {_p(int(min_compliance_score))}")
        else:
            clauses.append(f"compliance_score >= {_p(int(min_compliance_score))}")

    if max_compliance_score is not None:
        clauses.append(f"COALESCE(compliance_score, 0) <= {_p(int(max_compliance_score))}")

    if job_family:
        clauses.append(f"job_family = {_p(job_family)}")

    if seniority:
        clauses.append(f"seniority = {_p(seniority)}")

    if specialization:
        clauses.append(f"specialization = {_p(specialization)}")

    if first_seen_after:
        clauses.append(f"first_seen_at >= {_p(first_seen_after)}::timestamptz")

    if first_seen_before:
        clauses.append(f"first_seen_at < {_p(first_seen_before)}::timestamptz + INTERVAL '1 day'")

    if q:
        clauses.append("(title ILIKE :q_like OR company_name ILIKE :q_like)")
        params["q_like"] = f"%{q}%"

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def get_paid_api_jobs(
    *,
    status: str | None = None,
    q: str | None = None,
    company: str | None = None,
    title: str | None = None,
    source: str | None = None,
    remote_scope: str | None = None,
    remote_class: str | None = None,
    geo_class: str | None = None,
    compliance_status: str | None = None,
    min_compliance_score: int | None = None,
    max_compliance_score: int | None = None,
    job_family: str | None = None,
    seniority: str | None = None,
    specialization: str | None = None,
    first_seen_after: date | None = None,
    first_seen_before: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated full-field jobs for the paid API.

    Args:
        All filter args map directly to DB column filters.
        limit: Max rows to return (1–100).
        offset: Row offset for pagination.

    Returns:
        Tuple of (list of job dicts, total matching count).
    """
    where, params = _build_paid_jobs_where(
        status=status,
        q=q,
        company=company,
        title=title,
        source=source,
        remote_scope=remote_scope,
        remote_class=remote_class,
        geo_class=geo_class,
        compliance_status=compliance_status,
        min_compliance_score=min_compliance_score,
        max_compliance_score=max_compliance_score,
        job_family=job_family,
        seniority=seniority,
        specialization=specialization,
        first_seen_after=first_seen_after,
        first_seen_before=first_seen_before,
    )

    params["limit"] = limit
    params["offset"] = offset

    data_sql = f"{_PAID_JOB_SELECT}{where}\nORDER BY first_seen_at DESC\nLIMIT :limit OFFSET :offset"
    count_sql = f"SELECT COUNT(*) FROM jobs {where}"

    engine = _get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(data_sql), params).mappings().all()
        total = conn.execute(
            text(count_sql), {k: v for k, v in params.items() if k not in ("limit", "offset")}
        ).scalar_one()

    return [dict(row) for row in rows], int(total)
