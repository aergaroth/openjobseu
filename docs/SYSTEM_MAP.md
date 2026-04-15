# SYSTEM MAP (one-page)

Quick map of the entire OpenJobsEU system: **pipelines, tables, workers, APIs**.

---

## 1) Pipelines

### A. Runtime tick pipeline (main)
Trigger: `POST /internal/tick`

Order (`app/workers/pipeline.py`):
1. `run_employer_ingestion` (`app/workers/ingestion/employer.py`)
2. `run_lifecycle_pipeline` (`app/workers/lifecycle.py`)
3. `run_availability_pipeline` (`app/workers/availability.py`)
4. `run_market_metrics_worker` (`app/workers/market_metrics.py`)
5. `run_maintenance_pipeline` (`app/workers/maintenance.py`)
6. `run_frontend_export` (`app/workers/frontend_exporter.py`)

Flow:
`ATS adapters -> normalize + policy -> DB upsert -> lifecycle/availability -> market+company maintenance -> GCS Feed Export`

### B. Discovery pipeline (isolated)
Entrypoint: `app/workers/discovery/pipeline.py`
- `run_company_source_discovery`
- `run_careers_discovery`
- `run_ats_reverse_discovery`
- `run_ats_guessing`
- `run_dorking_discovery`
- `run_dorking_crt_discovery`
- `run_slug_harvest`
- `run_promote_discovered_slugs`

Goal:
- detecting ATS/provider+slug for companies,
- populating `company_ats`,
- updating `companies.careers_last_checked_at` / `companies.ats_guess_last_checked_at`.

Automation path:
- manual all-in-one run: `POST /internal/discovery/run`
- scheduled async phases: `POST /internal/tasks/company-sources` -> `POST /internal/tasks/careers` -> `POST /internal/tasks/ats-reverse` -> `POST /internal/tasks/guess`
- all scheduled phases share the same Cloud Tasks queue and rely on staggered cron windows plus queue concurrency `1`

---

## 2) Tables (data core)

### Core runtime
- `companies` – company catalog (metadata + discovery flags).
- `company_ats` – company -> ATS mapping (provider, slug, sync status).
- `jobs` – canonical job record (identity, compliance, lifecycle, salary, taxonomy).
- `job_sources` – `source/source_job_id -> job_id` mapping, source visibility tracking.
- `compliance_reports` – policy result per `job_uid + policy_version`.
- `job_snapshots` – historical job snapshots on fingerprint change.

### Analytics / audit
- `market_daily_stats` – daily market aggregates.
- `market_daily_stats_segments` – daily segment aggregates.
- `salary_parsing_cases` – salary parser cases (QA/analytics).

### Relations (summary)
`companies (1) -> (N) company_ats`

`companies (1) -> (N) jobs`

`jobs (1) -> (N) job_sources`

`jobs (1) -> (N) compliance_reports`

`jobs (1) -> (N) job_snapshots`

---

## 3) Workers

### Tick workers (pipeline runtime)
- **Employer ingestion worker** (`app/workers/ingestion/employer.py`)
  - Reads: `company_ats`, `companies`
  - Writes: `jobs`, `job_sources`, `compliance_reports`, `job_snapshots`, `company_ats.last_sync_at`

- **Lifecycle worker** (`app/workers/lifecycle.py`)
  - Reads/Writes: `jobs`
  - Operations: `new/active/stale/expired/unreachable`, repost markers

- **Availability worker** (`app/workers/availability.py`)
  - Reads: `jobs` (jobs to be verified)
  - Writes: `jobs.availability_status`, `last_verified_at`, `verification_failures`

- **Market metrics worker** (`app/workers/market_metrics.py`)
  - Reads: `jobs`, `job_sources`
  - Writes: `market_daily_stats`, `market_daily_stats_segments`

- **Maintenance worker** (`app/workers/maintenance.py`)
  - Reads/Writes: `companies`, `jobs`
  - Recomputes: company job stats, remote posture, signal scores

- **Frontend exporter** (`app/workers/frontend_exporter.py`)
  - Reads: `jobs`
  - Writes: `feed.json` to GCS during runtime ticks
  - Can also sync static frontend files during deploy-time publication when `sync_assets=True`

### Discovery workers
- `run_company_source_discovery` (`app/workers/discovery/company_sources.py`)
- `run_careers_discovery` (`app/workers/discovery/careers_crawler.py`)
- `run_ats_reverse_discovery` (`app/workers/discovery/ats_reverse.py`)
- `run_ats_guessing` (`app/workers/discovery/ats_guessing.py`)
- `run_dorking_discovery` (`app/workers/discovery/dorking.py`)
- `run_dorking_crt_discovery` (`app/workers/discovery/dorking_crt.py`)
- `run_slug_harvest` (`app/workers/discovery/slug_harvest.py`)
- `run_promote_discovered_slugs` (`app/workers/discovery/promote_discovered_slugs.py`)

### Utility/backfill workers (internal ops)
- direct system ops: `POST /internal/backfill-compliance`, `POST /internal/backfill-salary`, `POST /internal/backfill-department`, `POST /internal/backfill-remote-ratio`
- async task router: `POST /internal/tasks/{task_name}`
- strict task execution router: `POST /internal/tasks/{task_name}/execute`

---

## 4) APIs

### Access model

| Interface | Audience | Delivery path |
|---|---|---|
| Static frontend (`/`, JS/CSS assets) | Public | GCS + CDN |
| `GET /feed.json` | Public | GCS + CDN |
| `GET /health`, `GET /ready` | Internal/admin | Private Cloud Run |
| `GET /jobs`, `GET /companies`, `GET /jobs/stats/compliance-7d` | Internal/admin | Private Cloud Run |
| `GET /api/v1/jobs`, `GET /api/v1/analytics/*` | External (API key) | Private Cloud Run |
| `POST /internal/tick`, `POST /internal/tick/execute`, `GET /internal/audit*`, `POST /internal/tasks/*`, `POST /internal/backfill-*` | Internal/admin | Private Cloud Run |

Notes:
- `GET /jobs`, `GET /companies`, and `GET /jobs/stats/compliance-7d` exist in FastAPI, but are not public internet endpoints in `dev` or `prod` because Cloud Run invocation is restricted via IAM.
- `GET /feed.json` remains the public dataset contract used by the static frontend.
- `/api/v1/*` requires `Authorization: Bearer ojeu_<key>` — API key auth backed by the `api_keys` table; daily quota enforced via atomic `UPDATE … RETURNING` in PostgreSQL. See `docs/PAID_API.md`.
- Production and dev schedulers use `POST /internal/tasks/*` for automated discovery phases; `POST /internal/discovery/run` remains a manual synchronous operator endpoint.

---

## Minimal big picture

`External ATS -> Adapters -> Ingestion Worker -> jobs/job_sources/compliance_reports -> Lifecycle+Availability+Maintenance -> Market/Public/Internal surfaces`
