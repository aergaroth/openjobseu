from sqlalchemy.engine import Connection
from storage.db_engine import get_engine
from storage.db_logic import (
    activate_new_jobs_due_to_lifecycle,
    expire_jobs_due_to_lifecycle,
    reactivate_stale_jobs_due_to_lifecycle,
    stale_active_jobs_due_to_lifecycle,
)


def run_lifecycle_rules() -> None:
    """
    Backward-compatible wrapper.
    Apply lifecycle rules to all eligible jobs.
    """
    run_lifecycle_pipeline()


def run_lifecycle_pipeline(conn: Connection | None = None) -> None:
    """
    Apply lifecycle rules to all eligible jobs using efficient, set-based SQL queries.
    This is much more performant than fetching jobs and processing them in Python.
    """
    if conn is None:
        db_engine = get_engine()
        with db_engine.begin() as new_conn:
            run_lifecycle_pipeline(new_conn)
        return

    # Order matters: expire first to remove jobs from other transitions.
    expire_jobs_due_to_lifecycle(conn)
    stale_active_jobs_due_to_lifecycle(conn)
    activate_new_jobs_due_to_lifecycle(conn)
    reactivate_stale_jobs_due_to_lifecycle(conn)
