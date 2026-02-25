import ast
from pathlib import Path

from app.workers import availability, compliance_resolution, lifecycle


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
            seen.append((item["job_id"], item["status"], bool(item["failure"]), conn))

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


def test_compliance_resolution_uses_single_transaction_conn(monkeypatch):
    jobs = [
        {"job_id": "j1", "remote_class": "remote_only", "geo_class": "eu_region"},
        {"job_id": "j2", "remote_class": "unknown", "geo_class": "uk"},
    ]
    seen_conn_ids = []

    monkeypatch.setattr(
        compliance_resolution,
        "get_jobs_for_compliance_resolution",
        lambda limit, only_missing: jobs,
    )
    monkeypatch.setattr(
        compliance_resolution,
        "resolve_compliance",
        lambda remote_class, geo_class: {
            "compliance_status": "review",
            "compliance_score": 65,
        },
    )
    monkeypatch.setattr(compliance_resolution, "get_engine", lambda: _NoopEngine())

    def _fake_update(*, updates, conn=None):
        assert len(updates) == 2
        assert all(item["compliance_status"] == "review" for item in updates)
        assert all(item["compliance_score"] == 65 for item in updates)
        seen_conn_ids.extend([id(conn)] * len(updates))

    monkeypatch.setattr(
        compliance_resolution,
        "update_jobs_compliance_resolution",
        _fake_update,
    )

    summary = compliance_resolution.run_compliance_resolution(limit=10, only_missing=True)

    assert summary["checked"] == 2
    assert summary["updated"] == 2
    assert summary["only_missing"] is True
    assert len(set(seen_conn_ids)) == 1


def test_lifecycle_pipeline_uses_single_transaction_conn(monkeypatch):
    jobs = [
        {"job_id": "a"},
        {"job_id": "b"},
        {"job_id": "c"},
    ]
    transitions = {"a": "expired", "b": None, "c": "stale"}
    seen = []

    monkeypatch.setattr(lifecycle, "get_jobs_for_verification", lambda limit=50: jobs)
    monkeypatch.setattr(
        lifecycle,
        "apply_lifecycle_rules",
        lambda job, now: transitions[job["job_id"]],
    )
    monkeypatch.setattr(lifecycle, "get_engine", lambda: _NoopEngine())

    def _fake_update(*, updates, conn=None):
        for item in updates:
            seen.append((item["job_id"], item["status"], item["failure"], conn))

    monkeypatch.setattr(lifecycle, "update_jobs_availability", _fake_update)

    lifecycle.run_lifecycle_pipeline()

    assert [(item[0], item[1]) for item in seen] == [("a", "expired"), ("c", "stale")]
    assert all(item[3] is not None for item in seen)
    assert len({id(item[3]) for item in seen}) == 1


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
