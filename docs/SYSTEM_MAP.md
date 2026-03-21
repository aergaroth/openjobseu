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
5. `run_frontend_export` (`app/workers/frontend_exporter.py`)

Flow:
`ATS adapters -> normalize + policy -> DB upsert -> lifecycle/availability -> daily metrics -> GCS Feed Export`

### B. Discovery pipeline (isolated)
Entrypoint: `app/workers/discovery/pipeline.py`
- `run_careers_discovery`
- `run_ats_guessing`

Goal:
- detecting ATS/provider+slug for companies,
- populating `company_ats`,
- updating `companies.discovery_last_checked_at`.

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

- **Frontend exporter** (`app/workers/frontend_exporter.py`)
  - Reads: `jobs`
  - Writes: `feed.json` and static frontend files to GCS bucket

### Discovery workers
- `run_careers_discovery` (`app/workers/discovery/careers_crawler.py`)
- `run_ats_guessing` (`app/workers/discovery/ats_guessing.py`)

### Utility/backfill workers (internal ops)
- compliance backfill: `POST /internal/tasks/backfill-compliance`
- salary backfill: `POST /internal/tasks/backfill-salary`
- discovery trigger: `POST /internal/tasks/discovery`

---

## 4) APIs

### Public API
- `GET /health` – liveness
- `GET /ready` – readiness
- `GET /jobs` – job list (filters)
- `GET /feed.json` – zero-compute static job feed (served directly from GCS)
- `GET /jobs/stats/compliance-7d` – compliance 7d aggregates

- `POST /internal/tick` – runs runtime pipeline
- `GET /internal/audit` – audit panel HTML
- `GET /internal/audit/jobs` – listing + audit statistics
- `GET /internal/audit/filters` – filter dictionaries + dynamic source
- `GET /internal/audit/stats/company` – compliance ratio per company
- `GET /internal/audit/stats/source-7d` – compliance ratio per source (7d)
- `POST /internal/audit/tick-dev` – tick dev/debug
- `POST /internal/backfill-compliance` – worker backfill compliance
- `POST /internal/backfill-salary` – worker backfill salary

---

## Minimal big picture

`External ATS -> Adapters -> Ingestion Worker -> jobs/job_sources/compliance_reports -> Lifecycle+Availability -> Market Metrics -> Public/Internal APIs`
