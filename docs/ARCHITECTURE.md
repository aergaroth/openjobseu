# System Architecture – OpenJobsEU

## Overview

OpenJobsEU is a backend-first, compliance-focused pipeline for aggregating legally accessible remote job offers with EU relevance signals.

The runtime is intentionally read-only on the public side and operationally explicit on the internal side.

---

## High-Level Flow

![Architecture diagram](./architecture.png)

Pipeline mode flow:

ATS Adapters -> Employer Ingestion Worker -> Policy Signals -> DB Upsert -> Post-Ingestion Workers -> Read APIs

---

## Runtime Orchestration

- Runtime entrypoint: `app.workers.pipeline.run_pipeline`
- Tick pipeline orchestration:
  - runs `run_employer_ingestion()`
  - runs `run_post_ingestion()`
- Ingestion worker is single-source and ATS-backed (`employer_ing`)

---

## Ingestion Layer

### `employer_ing`

Runtime path:
- loads active ATS companies from `companies` table (`is_active=true`, `ats_provider`, `ats_slug`)
  - batched to 100 companies per tick, ordered by `company_ats.updated_at ASC`
- adapters resolved via `app/adapters/ats/registry.py`
- current adapter implementations:
  - `app/adapters/ats/greenhouse.py`
  - `app/adapters/ats/lever.py`
  - `app/adapters/ats/workable.py`
  - `app/adapters/ats/ashby.py`
  - `app/adapters/ats/personio.py`
  - `app/adapters/ats/recruitee.py`
- normalization happens inside adapters (`normalize()`)
- policy tagging uses `app/domain/compliance/engine.py` (`apply_policy`)

`employer_ing` can hard-skip records with `geo_restriction_hard` signals before DB upsert.

---

## Storage Layer

The storage backend uses SQLAlchemy Core and PostgreSQL.

Database modes:
- `DB_MODE=standard` + `DATABASE_URL=postgresql+psycopg://...`
- `DB_MODE=cloudsql` + Cloud SQL connector settings (`INSTANCE_CONNECTION_NAME`, `DB_NAME`, `DB_USER`)

Schema initialization is migration-file based (`storage/migrations/*.sql`) and tracked in `schema_migrations`.

Core tables:
- `jobs`
- `companies`

`jobs.company_id` references `companies.company_id` (nullable FK).

---

## Classification and Compliance

At write-time, job rows are normalized to canonical classes (`remote_class`, `geo_class`) during upsert.

Compliance policy is applied during ingestion before persistence.

---

## Post-Ingestion Workers

`run_post_ingestion()` executes:
- availability checks (`app/workers/availability.py`)
- lifecycle transitions (`app/workers/lifecycle.py`)

Lifecycle states in runtime:
- `new`, `active`, `stale`, `expired`, `unreachable`

---

## API Layer

Public endpoints:
- `GET /health`
- `GET /ready`
- `GET /jobs`
- `GET /jobs/feed`
- `GET /jobs/stats/compliance-7d`

Feed behavior:
- visible jobs only (`new`, `active`)
- minimum compliance score: `80`
- cache header: `Cache-Control: public, max-age=300`

Internal endpoints:
- `POST /internal/tick` (`format=auto|text|json`)
- `GET /internal/audit`
- `GET /internal/audit/jobs`
- `GET /internal/audit/filters`
- `GET /internal/audit/stats/company`
- `GET /internal/audit/stats/source-7d`
- `POST /internal/audit/tick-dev`
- `POST /internal/backfill-compliance`
- `POST /internal/backfill-salary`
- `GET /internal/discovery/audit`
- `GET /internal/discovery/candidates`
- `POST /internal/discovery/careers`
- `POST /internal/discovery/guess`
- `POST /internal/discovery/run`

Audit panel data shape:
- `/internal/audit/filters` returns canonical filter lists and dynamic `source` values from DB
- `/internal/audit/stats/company` provides aggregated compliance ratio by `companies.legal_name` (`HAVING COUNT(*) > 10` by default)
- `/internal/audit/stats/source-7d` provides aggregated compliance ratio by source for rows with `first_seen_at` in last 7 days

---

## Logging and Metrics

Logging mode:
- text formatter in local runtime (`APP_RUNTIME=local` or non-container)
- JSON formatter in container/cloud runtime

Tick payload/summary includes:
- employer ingestion counters and policy metrics
- timing metrics

---

## Deployment Shape

Infrastructure is managed with Terraform in split environments:
- `infra/gcp/dev`
- `infra/gcp/prod`

Production scheduler triggers `POST /internal/tick` every 15 minutes.

---

## Architecture Map (Detailed)

Poniższa sekcja konsoliduje dawną zawartość `ARCHITECTURE_MAP.md` w jednym pliku źródłowym.

### Table of Contents
- [1. System overview](#1-system-overview)
- [2. Repository structure](#2-repository-structure)
- [3. Runtime pipeline architecture](#3-runtime-pipeline-architecture)
- [4. Ingestion architecture](#4-ingestion-architecture)
- [5. Discovery architecture](#5-discovery-architecture)
- [6. Worker system](#6-worker-system)
- [7. Data model overview](#7-data-model-overview)
- [8. API layer](#8-api-layer)
- [9. Infrastructure layer](#9-infrastructure-layer)
- [10. Future analytics layer](#10-future-analytics-layer)

### 1. System overview

OpenJobsEU is a backend-first FastAPI service that ingests remote job offers from ATS sources, applies deterministic compliance logic, persists canonical job records in PostgreSQL, and exposes read/audit APIs.

Primary runtime flow in code:
- API service bootstrap and readiness gate: `app/main.py`
- Internal tick trigger: `app/internal.py`
- Tick orchestration: `app/workers/pipeline.py`
- Main ingestion worker: `app/workers/ingestion/employer.py`
- Post-ingestion workers: `app/workers/lifecycle.py`, `app/workers/availability.py`, `app/workers/market_metrics.py`

### 2. Repository structure

#### `app/` (application runtime)
- `app/main.py` – FastAPI app, DB bootstrap (`init_db`), readiness middleware, router registration.
- `app/internal.py` – internal/ops endpoints (`/internal/tick`, audit and backfill endpoints).
- `app/api/` – public read API (`app/api/jobs.py`).
- `app/workers/` – runtime workers and orchestrators.
- `app/adapters/` – ATS adapter abstraction and implementations.
- `app/domain/` – pure business logic (compliance, identity, taxonomy, salary, company logic).
- `app/utils/` – helper utilities (tick formatting, backfills, cleaning).

#### `storage/` (data access + schema)
- `storage/db_engine.py` – SQLAlchemy engine factory/DB mode handling.
- `storage/db_logic.py` – migration bootstrap + compatibility facade re-exporting repositories.
- `storage/repositories/` – table-level access and mutation logic.
- `storage/migrations/` – SQL migrations (`001`–`021`).

#### `infra/` (Terraform)
- `infra/gcp/dev/` – Cloud Run dev service and state backend.
- `infra/gcp/prod/` – Cloud Run prod + Cloud Scheduler job (`scheduler.tf`) triggering `/internal/tick` every 15 minutes.

#### `validator/` (test suite)
- Integration/unit tests for adapters, workers, policy, DB logic, orchestration.

#### `pipelines` and related folders
- There is no top-level `pipelines/` directory.
- Pipeline/orchestration code exists in:
  - `app/workers/pipeline.py` (main runtime tick)
  - `app/workers/discovery/pipeline.py` (discovery pipeline, standalone entrypoint)

#### `ingestion/` (legacy/placeholder tree)
- Contains only subdirectories `ingestion/adapters/` and `ingestion/loaders/` in current tree (no active runtime entrypoint in scanned files).

### 3. Runtime pipeline architecture

#### Runtime start
1. FastAPI app starts (`app/main.py`), runs asynchronous DB bootstrap loop:
   - `_run_db_bootstrap_once()` calls `init_db()` + `db_healthcheck()`.
2. Readiness is enforced by middleware until bootstrap succeeds (`/health` and `/ready` are exempt).

#### Tick trigger and orchestration
- Trigger path: `POST /internal/tick` in `app/internal.py`.
- Endpoint calls `run_pipeline()` from `app/workers/pipeline.py`.

#### Execution order (`PIPELINE_STEPS`)
Defined in `app/workers/pipeline.py`:
1. `run_employer_ingestion` (`app/workers/ingestion/employer.py`)
2. `run_lifecycle_pipeline` (`app/workers/lifecycle.py`)
3. `run_availability_pipeline` (`app/workers/availability.py`)
4. `run_market_metrics_worker` (`app/workers/market_metrics.py`)

The orchestrator aggregates `actions` and step-level `metrics`; failures are captured per step as `{"status": "error"}` while the pipeline continues to next steps.

#### Data flow between steps
- Ingestion writes/updates job and compliance data (`jobs`, `job_sources`, `compliance_reports`, optionally `job_snapshots`).
- Lifecycle updates statuses and repost markers on `jobs`.
- Availability checks selected jobs and updates `availability_status`, `last_verified_at`, `verification_failures`.
- Market metrics reads operational tables and writes daily aggregates to `market_daily_stats` and `market_daily_stats_segments`.

### 4. Ingestion architecture

#### ATS adapter layer
- Base contract: `app/adapters/ats/base.py` (`fetch`, `normalize`, `probe_jobs`).
- Registry: `app/adapters/ats/registry.py`.
- Implementations in tree:
  - `app/adapters/ats/greenhouse.py`
  - `app/adapters/ats/lever.py`
  - `app/adapters/ats/workable.py`
  - `app/adapters/ats/ashby.py`
  - `app/adapters/ats/personio.py`
  - `app/adapters/ats/recruitee.py`

#### Ingestion runtime flow
Main worker: `app/workers/ingestion/employer.py`
1. Load active ATS-company mappings via `load_active_ats_companies` (`storage/repositories/ats_repository.py`) batched by 100 oldest synced records.
2. For each company:
   - resolve adapter from registry,
   - fetch raw jobs incrementally via `fetch_company_jobs` using `last_sync_at` as a cursor,
   - open DB transaction and process jobs via `process_company_jobs` (`app/workers/ingestion/process_loop.py`),
   - mark sync timestamp (`mark_ats_synced`) to rotate the queue (`updated_at`) and advance the fetch cursor (`last_sync_at`).

#### Normalization + identity + policy/compliance
Per job in `process_company_jobs`:
1. `adapter.normalize(raw_job)`
2. `compute_schema_hash(raw)` (`app/domain/jobs/identity.py`)
3. `process_ingested_job(normalized, source)` (`app/domain/jobs/job_processing.py`), which performs:
   - canonical ID: `compute_canonical_job_id`
   - job UID/fingerprint: `compute_job_uid`, `compute_job_fingerprint`
   - compliance policy: `apply_policy` (`app/domain/compliance/engine.py`)
   - taxonomy: `classify_taxonomy`
   - salary extraction: `extract_structured_salary` / `extract_salary`
   - salary transparency: `detect_salary_transparency`
   - quality score: `compute_job_quality_score`

#### DB persistence
- All processed jobs (including rejected ones) are upserted by `upsert_job` (`storage/repositories/jobs_repository.py`) to support comprehensive market analytics and auditability.
- Compliance reports are persisted for all processed jobs with `insert_compliance_report` (`storage/repositories/compliance_repository.py`).
- `upsert_job` also:
  - maintains `job_sources` mapping,
  - snapshots previous version into `job_snapshots` when fingerprint changes.

#### Post-ingestion workers
Executed after ingestion by main pipeline:
- lifecycle transitions (`app/workers/lifecycle.py`)
- availability verification (`app/workers/availability.py`)
- daily market aggregations (`app/workers/market_metrics.py`)

#### Text diagram
`ATS adapter` → `normalize` → `compliance` → `persistence` → `lifecycle workers`

Expanded path in code:
`adapter.fetch` → `adapter.normalize` → `process_ingested_job` → `upsert_job + insert_compliance_report` → `run_lifecycle_pipeline/run_availability_pipeline/run_market_metrics_worker`

### 5. Discovery architecture

Discovery orchestrator: `app/workers/discovery/pipeline.py`
- `run_careers_discovery()` (`careers_crawler.py`)
- `run_ats_guessing()` (`ats_guessing.py`)

#### Careers crawler flow (`app/workers/discovery/careers_crawler.py`)
1. Load candidate companies via `load_discovery_companies` where:
   - `bootstrap = FALSE`
   - `is_active = TRUE`
   - `ats_provider IS NULL`
   - `careers_url IS NOT NULL`
2. Fetch careers page.
3. Detect provider/slug from redirects, URL patterns, HTML content, and shallow crawl candidate links.
4. Validate slug (`_is_valid_slug`).
5. Probe ATS via `probe_ats` (`app/workers/discovery/ats_probe.py`, adapter `probe_jobs`).
6. Apply quality filters:
   - `jobs_total >= 5`
   - `remote_hits >= 1`
   - `recent_job_at` within 120 days
7. Insert into `company_ats` via `insert_discovered_company_ats`.
8. Update `companies.discovery_last_checked_at`.

#### ATS guessing flow (`app/workers/discovery/ats_guessing.py`)
1. Generate slug candidates from company name.
2. Probe providers in fixed list (`greenhouse`, `lever`, `workable`, `ashby`, `personio`, `recruitee`).
3. Apply same quality thresholds as crawler.
4. Insert candidate into `company_ats` on successful probe.
5. Update `companies.ats_guess_last_checked_at`.

### 6. Worker system

#### Main tick workers (trigger: `POST /internal/tick` or Cloud Scheduler in prod)
1. **Employer ingestion worker** – `app/workers/ingestion/employer.py`
   - Reads: `company_ats`, `companies`
   - Writes: `jobs`, `job_sources`, `compliance_reports`, `job_snapshots`, `company_ats.last_sync_at`

2. **Lifecycle worker** – `app/workers/lifecycle.py`
   - Reads/Writes: `jobs`
   - Operations: expire stale/unavailable jobs, stale active jobs, activate new, reactivate stale, mark reposts

3. **Availability worker** – `app/workers/availability.py`
   - Reads: `jobs` (active/stale requiring verification)
   - Writes: `jobs.availability_status`, `last_verified_at`, `verification_failures`, `updated_at`

4. **Market metrics worker** – `app/workers/market_metrics.py`
   - Reads: `jobs`, `job_sources`
   - Writes: `market_daily_stats`, `market_daily_stats_segments`

#### Discovery workers (separate discovery pipeline)
- `run_careers_discovery` and `run_ats_guessing`
  - Reads: `companies`
  - Writes: `company_ats`, `companies.discovery_last_checked_at`

#### Utility/backfill workers exposed via internal API
- `POST /internal/backfill-compliance` → `app/utils/backfill_compliance.py`
- `POST /internal/backfill-salary` → `app/utils/backfill_salary.py`

### 7. Data model overview

Schema source: `storage/migrations/*.sql` + repository usage in `storage/repositories/*.py`.

#### `jobs`
- Purpose: canonical job record used by feed, policy outputs, lifecycle and analytics.
- Defined in: `001_initial_jobs.sql`, extended by `003`, `009`, `010`, `011`, `018` and indexes in `021`.
- Main fields (selected):
  - identity/source: `job_id` (PK), `source`, `source_job_id`, `source_url`, `job_uid`, `job_fingerprint`, `source_schema_hash`
  - content: `title`, `company_name`, `description`, `remote_scope`
  - lifecycle/availability: `status`, `first_seen_at`, `last_seen_at`, `last_verified_at`, `verification_failures`, `availability_status`, `is_repost`, `repost_count`
  - compliance: `remote_class`, `geo_class`, `policy_version`, `compliance_status`, `compliance_score`
  - taxonomy/quality: `job_family`, `job_role`, `seniority`, `specialization`, `job_quality_score`
  - salary: `salary_min`, `salary_max`, `salary_currency`, `salary_period`, `salary_source`, `salary_min_eur`, `salary_max_eur`, `salary_transparency_status`
  - relation: `company_id` (FK → `companies.company_id`)

#### `companies`
- Purpose: company registry used for ingestion and discovery candidate selection.
- Defined in: `002_companies.sql`, extended by `022_split_discovery_timestamps.sql` and `024_company_job_stats.sql`.
- Main fields: `company_id` (PK), `legal_name`, `brand_name`, `hq_country`, `remote_posture`, `ats_provider`, `ats_slug`, `careers_url`, `is_active`, `bootstrap`, `careers_last_checked_at`, `ats_guess_last_checked_at`, aggregated stats (`total_jobs_count`, `rejected_jobs_count`, `last_active_job_at`), timestamps.

#### `company_ats`
- Purpose: normalized mapping of company to ATS endpoints/configurations (multi-ATS structure).
- Defined in: `003_ingestion_and_compliance.sql`; unique provider+slug in `016`.
- Main fields: `company_ats_id` (PK), `company_id` (FK), `provider`, `ats_slug`, `ats_api_url`, `careers_url`, `is_active`, `last_sync_at` (incremental cursor), `updated_at` (queue ordering), timestamps.

#### `job_sources`
- Purpose: source-to-canonical mapping and source-level lifecycle visibility.
- Defined in: `005_job_sources_and_fingerprint_uniqueness.sql`, extended by `017_job_sources_seen_count.sql`.
- Main fields: composite PK (`source`, `source_job_id`), `job_id` (FK → jobs), `source_url`, `first_seen_at`, `last_seen_at`, `seen_count`, timestamps.

#### `job_snapshots`
- Purpose: historical snapshots when job fingerprint/content changes during upsert.
- Defined in: `014_job_snapshots.sql`.
- Main fields: `snapshot_id` (PK), `job_id`, `job_fingerprint`, `title`, `company_name`, salary fields, `captured_at`.

#### `compliance_reports`
- Purpose: persisted policy decision output per canonical identity and policy version.
- Defined in: `003_ingestion_and_compliance.sql`, uniqueness strengthened in `008_compliance_reports_unique_index.sql`.
- Main fields: `report_id` (PK), `job_id` (FK → jobs), `job_uid`, `policy_version`, `remote_class`, `geo_class`, `hard_geo_flag`, scoring fields, `decision_vector`, `created_at`.
- Constraint: unique index on `(job_uid, policy_version)`.

#### Additional analytics/audit tables present
- `salary_parsing_cases` (`012_salary_parsing_cases.sql`)
- `market_daily_stats` (`019_market_daily_stats.sql`)
- `market_daily_stats_segments` (`020_market_daily_stats_segments.sql`)

### 8. API layer

#### Application composition
- Routers mounted in `app/main.py`:
  - `app/api/jobs.py` under `/jobs`
  - `app/internal.py` under `/internal`

#### Public endpoints
- `GET /health` (`app/main.py`) – liveness.
- `GET /ready` (`app/main.py`) – readiness state.
- `GET /jobs` (`app/api/jobs.py`) – filtered list from `storage.db_logic.get_jobs` (`jobs` table + optional `job_sources` source filter).
- `GET /jobs/feed` – visible jobs feed with `min_compliance_score=80`, cache headers.
- `GET /jobs/stats/compliance-7d` – compliance aggregate from `jobs`.

#### Internal endpoints
- `POST /internal/tick` – execute full runtime pipeline.
- `GET /internal/audit` – HTML audit panel (`audit_tool/offer_audit_panel.html`).
- `GET /internal/audit/jobs` – audit listing and counts (reads `jobs` + `job_sources`).
- `GET /internal/audit/filters` – filter registry + dynamic source list.
- `GET /internal/audit/stats/company` – company compliance ratios (`jobs` + `companies`).
- `GET /internal/audit/stats/source-7d` – source compliance ratios (`jobs` + `job_sources`).
- `POST /internal/audit/tick-dev` – tick endpoint with forced text output.
- `POST /internal/backfill-compliance` – backfill worker trigger.
- `POST /internal/backfill-salary` – salary backfill worker trigger.

### 9. Infrastructure layer

Terraform layout:
- `infra/gcp/dev/*` – dev Cloud Run service + GCS backend.
- `infra/gcp/prod/*` – prod Cloud Run service + scheduler.

Key runtime infra facts from code:
- Cloud Run exposes the FastAPI service publicly (`roles/run.invoker` to `allUsers`).
- DB URL is provided via Secret Manager env var (`DATABASE_URL`).
- Prod scheduler (`infra/gcp/prod/scheduler.tf`) triggers `POST /internal/tick` every 15 minutes.

### 10. Future analytics layer

Already implemented analytics foundations in current codebase:
- Aggregation worker: `app/workers/market_metrics.py`
- Aggregate repositories:
  - `storage/repositories/market_repository.py`
  - `storage/repositories/market_segments_repository.py`
- Aggregate tables:
  - `market_daily_stats`
  - `market_daily_stats_segments`

This forms the current base for a broader analytics layer, while existing public API still focuses on jobs feed and compliance stats.

### Architectural boundaries (cross-layer summary)

- **Adapter layer (`app/adapters/ats`)**: provider-specific fetch/normalize/probe logic only.
- **Domain layer (`app/domain`)**: pure transformations/classification/scoring, no DB IO.
- **Worker layer (`app/workers`)**: orchestration and transaction-scoped execution.
- **Data layer (`storage/repositories`, `storage/migrations`)**: SQL persistence, retrieval, schema evolution.
- **API layer (`app/api`, `app/internal`, `app/main`)**: HTTP contracts and operational control surface.

The key separation visible in code is: workers call domain logic and repositories; domain logic does not call storage directly.
