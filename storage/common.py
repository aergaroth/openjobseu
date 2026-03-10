from sqlalchemy.engine import Connection

def _string_like(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)

def _derive_source_fields(job: dict) -> tuple[str, str, str | None]:
    source = (_string_like(job.get("source")) or "").strip()
    source_job_id = (_string_like(job.get("source_job_id")) or "").strip()
    source_url = _string_like(job.get("source_url"))

    if not source:
        raise ValueError("job.source is required")
    if not source_job_id:
        raise ValueError("job.source_job_id is required")

    return source, source_job_id, source_url

def _require_open_conn(conn: Connection | None, *, op_name: str) -> Connection:
    if conn is None:
        raise ValueError(f"{op_name} requires an explicit open transaction connection (conn).")
    return conn
