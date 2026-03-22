import logging
import random
import time
from functools import wraps

from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, OperationalError

logger = logging.getLogger(__name__)


def retry_on_db_timeout(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    jitter: float = 0.5,
):
    """
    Dekorator ponawiający wykonanie funkcji w przypadku przejściowych błędów bazy danych
    (timeouty, utrata połączenia, deadlocki) z użyciem Exponential Backoff i Jitter.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DBAPIError) as exc:
                    if attempt == max_retries:
                        logger.error(
                            "db_retry_exhausted",
                            extra={
                                "func": func.__name__,
                                "attempts": attempt,
                                "error": str(exc),
                            },
                        )
                        raise

                    sleep_time = delay + random.uniform(0, jitter)
                    logger.warning(
                        "db_transient_error_retrying",
                        extra={
                            "func": func.__name__,
                            "attempt": attempt,
                            "sleep_time": round(sleep_time, 2),
                            "error": str(exc),
                        },
                    )

                    time.sleep(sleep_time)
                    delay *= backoff_factor

        return wrapper

    return decorator


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
