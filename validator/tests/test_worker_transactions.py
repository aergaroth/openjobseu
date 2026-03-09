import ast
from pathlib import Path

from app.workers import availability, lifecycle


class _NoopTx:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


class _NoopEngine:
    def begin(self):
        return _NoopTx()


_WRITE_HELPERS_REQUIRING_CONN = {
    "upsert_job",
    "update_job_availability",
    "update_jobs_availability",
    "update_job_compliance_resolution",
    "update_jobs_compliance_resolution",
}


def _called_function_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_availability_pipeline_uses_single_transaction_conn(monkeypatch):
    jobs = [
        {"job_id": "a"},
        {"job_id": "b"},
        {"job_id": "c"},
    ]
    statuses = {
        "a": "active",
        "b": "expired",
        "c": "unreachable",
    }
    seen = []

    monkeypatch.setattr(availability, "get_jobs_for_verification", lambda limit=20: jobs)
    monkeypatch.setattr(
        availability,
        "check_job_availability",
        lambda job: statuses[job["job_id"]],
    )
    monkeypatch.setattr(availability, "get_engine", lambda: _NoopEngine())

    def _fake_update(*, updates, conn=None):
        for item in updates:
            seen.append((item["job_id"], item["availability_status"], bool(item["failure"]), conn))

    monkeypatch.setattr(availability, "update_jobs_availability", _fake_update)

    summary = availability.run_availability_pipeline()

    assert summary == {
        "checked": 3,
        "active": 1,
        "expired": 1,
        "unreachable": 1,
    }
    assert [item[0] for item in seen] == ["a", "b", "c"]
    assert all(item[3] is not None for item in seen)
    assert len({id(item[3]) for item in seen}) == 1


def test_lifecycle_pipeline_uses_single_transaction_conn(monkeypatch):
    calls = []

    def _fake_expire(conn):
        calls.append(("expire", conn))

    def _fake_stale(conn):
        calls.append(("stale", conn))

    def _fake_activate(conn):
        calls.append(("activate", conn))

    def _fake_reactivate(conn):
        calls.append(("reactivate", conn))

    monkeypatch.setattr(lifecycle, "expire_jobs_due_to_lifecycle", _fake_expire)
    monkeypatch.setattr(lifecycle, "stale_active_jobs_due_to_lifecycle", _fake_stale)
    monkeypatch.setattr(lifecycle, "activate_new_jobs_due_to_lifecycle", _fake_activate)
    monkeypatch.setattr(lifecycle, "reactivate_stale_jobs_due_to_lifecycle", _fake_reactivate)
    monkeypatch.setattr(lifecycle, "get_engine", lambda: _NoopEngine())

    lifecycle.run_lifecycle_pipeline()

    assert len(calls) == 4
    assert [c[0] for c in calls] == ["expire", "stale", "activate", "reactivate"]
    
    # Verify that all calls shared the same connection object
    assert all(c[1] is not None for c in calls)
    assert len({id(c[1]) for c in calls}) == 1


def test_worker_write_helpers_are_called_with_explicit_conn_kwarg():
    repo_root = Path(__file__).resolve().parents[2]
    workers_root = repo_root / "app" / "workers"

    violations: list[str] = []

    for file_path in workers_root.rglob("*.py"):
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        relative = file_path.relative_to(repo_root)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_name = _called_function_name(node)
            if func_name not in _WRITE_HELPERS_REQUIRING_CONN:
                continue

            conn_kwarg = next((kw for kw in node.keywords if kw.arg == "conn"), None)
            if conn_kwarg is None:
                violations.append(
                    f"{relative}:{node.lineno} -> {func_name} call without conn kwarg",
                )
                continue

            if isinstance(conn_kwarg.value, ast.Constant) and conn_kwarg.value.value is None:
                violations.append(
                    f"{relative}:{node.lineno} -> {func_name} call with conn=None",
                )

    assert not violations, "Worker DB write calls must pass active conn:\n" + "\n".join(violations)
