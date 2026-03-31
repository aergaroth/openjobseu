# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenJobsEU is a compliance-first EU-wide remote job aggregation platform built on a serverless GCP stack. The core design is a **zero-compute public architecture**: a private Cloud Run backend periodically generates a static `feed.json` pushed to GCS + CDN. The backend is never directly reachable by end users.

## Commands

### Dependencies (uses `uv`, not pip)
```bash
make deps      # Compile requirements*.in → requirements*.txt and sync venv
make compile   # Compile only (no sync)
make sync      # Sync venv only
```

### Lint & Format
```bash
make lint      # Run Ruff linter + formatter via pre-commit
make check     # Run ALL pre-commit hooks (lint, format, no-prints check, pytest)
```

### Tests
```bash
pytest                                              # Full test suite (requires PostgreSQL)
pytest validator/tests/test_compliance_engine.py   # Single test file
pytest -k "test_name"                              # Single test by name

# Spin up local PostgreSQL for tests
docker run --rm --name openjobspg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=testdb -p 5432:5432 -d postgres:16
```

Tests load `.env` automatically via `pytest-dotenv`. Minimum `.env` for testing:
```
DB_MODE=standard
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/testdb
APP_RUNTIME=local
```

### Run Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
# or
docker compose up
```

On startup, the app auto-runs `alembic upgrade head` and blocks all requests (except `/health`, `/ready`) until the DB is ready.

## Architecture

### Request Path (Two Distinct Surfaces)

**Public (zero-compute):** Static files served from GCS + CDN — `index.html`, `style.css`, `feed.js`, `feed.json`. The frontend JS fetches `feed.json` directly from GCS. No Cloud Run is involved for public requests.

**Private (Cloud Run, IAM-gated):** All admin, operational, and pipeline endpoints. Only accessible by the Cloud Scheduler service account and GitHub Actions OIDC.

### Main Pipeline (triggered every 35 min via Cloud Scheduler → `POST /internal/tick`)

```
run_employer_ingestion()     → Fetch from ATS adapters, normalize, apply compliance
run_lifecycle_pipeline()     → Transition job statuses (new → active → stale → expired)
run_availability_pipeline()  → Verify job URLs (200/404/timeout)
run_market_metrics_worker()  → Aggregate daily statistics
run_maintenance_pipeline()   → Refresh company stats and scores
run_frontend_export()        → Generate feed.json → push to GCS
```

Orchestrated in [app/workers/pipeline.py](app/workers/pipeline.py).

### Layer Responsibilities

| Layer | Path | Rule |
|---|---|---|
| API | `app/api/` | HTTP only — delegates immediately to workers |
| Workers | `app/workers/` | Orchestration and I/O coordination |
| Domain | `app/domain/` | Pure business logic — **no DB or HTTP calls** |
| Adapters | `app/adapters/ats/` | One class per ATS provider, normalized output |
| Storage | `storage/repositories/` | All DB access via repository classes |

The domain layer (`app/domain/`) must stay pure. Compliance engine, taxonomy classifier, salary parser, and job identity logic have no side effects.

### ATS Adapters

Each ATS provider has a class in `app/adapters/ats/` (Greenhouse, Lever, Workable, Ashby, Personio, Recruitee, SmartRecruiters). All implement the contract in `base.py` and are registered in `registry.py`.

### Compliance Engine

Located in `app/domain/compliance/`. Takes normalized job data, returns a `compliance_status` (approved|review|rejected) and score (0–100). The engine is **deterministic and policy-versioned** — every decision is stored in `compliance_reports` with `policy_version`. The public feed shows jobs with score ≥ 80.

### Job Identity

Jobs are deduplicated across ATS providers using two keys computed in `app/domain/jobs/identity.py`:
- `job_uid`: Stable canonical ID (survives minor content edits)
- `job_fingerprint`: Content hash (triggers snapshot on change)

### Database Schema (key tables)

- `jobs` — canonical job record with all classifications, lifecycle, compliance, salary, taxonomy fields
- `companies` — company registry with ATS mappings and discovery state
- `company_ats` — multi-ATS mapping per company (a company can have multiple ATS slugs)
- `job_sources` — source-to-canonical mapping (same job from multiple ATS providers)
- `compliance_reports` — policy decision output, keyed on `(job_uid, policy_version)`
- `job_snapshots` — historical snapshots captured on fingerprint change
- `market_daily_stats` / `market_daily_stats_segments` — daily aggregates

Migrations are in `storage/alembic/versions/`, managed with Alembic.

## Code Conventions

- **No `print()` statements** — enforced by pre-commit hook. Use structured logging from `app/logging.py`.
- **Commit messages** must follow Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, etc.) — enforced by Commitizen.
- **Line length**: 120 characters (Ruff).
- **Unused imports (F401)** are not auto-fixed by `ruff --fix` — remove manually.
- Tests live in `validator/tests/`, not alongside source files.
- `APP_RUNTIME=local` disables all auth and security enforcement — safe for dev, never use in cloud.

## Branching

- `main` → production, protected
- `develop` → integration branch, all PRs target here
- Both branches require passing CI (`pytest`) before merge
- `sync_main_to_develop.yml` auto-syncs release changes from `main` back to `develop`
