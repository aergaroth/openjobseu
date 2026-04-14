# Test selection

- Fast feedback (skip DB integration):
  - `pytest -m "not integration_db"`
- Full integration suite (only DB integration tests):
  - `pytest -m integration_db`
- Full test suite:
  - `pytest`

Use `integration_db` for tests that intentionally depend on real PostgreSQL behavior.
