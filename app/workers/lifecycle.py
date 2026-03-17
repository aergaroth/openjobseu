from storage.db_logic import (
    activate_new_jobs_due_to_lifecycle,
    expire_jobs_due_to_lifecycle,
    mark_reposts_due_to_lifecycle,
    reactivate_stale_jobs_due_to_lifecycle,
    stale_active_jobs_due_to_lifecycle,
)


def run_lifecycle_rules() -> None:
    """
    Backward-compatible wrapper.
    Apply lifecycle rules to all eligible jobs.
    """
    run_lifecycle_pipeline()


def run_lifecycle_pipeline() -> None:
    """
    Apply lifecycle rules to all eligible jobs using efficient, set-based SQL queries.
    This is much more performant than fetching jobs and processing them in Python.
    """
    # Order matters: expire first to remove jobs from other transitions.
    expire_jobs_due_to_lifecycle()
    stale_active_jobs_due_to_lifecycle()
    activate_new_jobs_due_to_lifecycle()
    reactivate_stale_jobs_due_to_lifecycle()
    mark_reposts_due_to_lifecycle()
