# SYSTEM MAP (one-page)

Szybka mapa całego systemu OpenJobsEU: **pipelines, tables, workers, APIs**.

---

## 1) Pipelines

### A. Runtime tick pipeline (główny)
Trigger: `POST /internal/tick`

Kolejność (`app/workers/pipeline.py`):
1. `run_employer_ingestion` (`app/workers/ingestion/employer.py`)
2. `run_lifecycle_pipeline` (`app/workers/lifecycle.py`)
3. `run_availability_pipeline` (`app/workers/availability.py`)
4. `run_market_metrics_worker` (`app/workers/market_metrics.py`)

Przepływ:
`ATS adapters -> normalize + policy -> DB upsert -> lifecycle/availability -> daily metrics`

### B. Discovery pipeline (osobny)
Entrypoint: `app/workers/discovery/pipeline.py`
- `run_careers_discovery`
- `run_ats_guessing`

Cel:
- wykrywanie ATS/provider+slug dla firm,
- zasilanie `company_ats`,
- aktualizacja `companies.discovery_last_checked_at`.

---

## 2) Tables (rdzeń danych)

### Core runtime
- `companies` – katalog firm (metadane + discovery flags).
- `company_ats` – mapowanie firma -> ATS (provider, slug, sync status).
- `jobs` – kanoniczny rekord oferty (identity, compliance, lifecycle, salary, taxonomy).
- `job_sources` – mapowanie `source/source_job_id -> job_id`, śledzenie widoczności źródła.
- `compliance_reports` – wynik polityki per `job_uid + policy_version`.
- `job_snapshots` – historyczne snapshoty ofert przy zmianie fingerprintu.

### Analytics / audit
- `market_daily_stats` – dzienne agregaty rynku.
- `market_daily_stats_segments` – dzienne agregaty segmentowe.
- `salary_parsing_cases` – przypadki parsera wynagrodzeń (QA/analityka).

### Relacje (skrót)
`companies (1) -> (N) company_ats`

`companies (1) -> (N) jobs`

`jobs (1) -> (N) job_sources`

`jobs (1) -> (N) compliance_reports`

`jobs (1) -> (N) job_snapshots`

---

## 3) Workers

### Tick workers (pipeline runtime)
- **Employer ingestion worker** (`app/workers/ingestion/employer.py`)
  - Czyta: `company_ats`, `companies`
  - Pisze: `jobs`, `job_sources`, `compliance_reports`, `job_snapshots`, `company_ats.last_sync_at`

- **Lifecycle worker** (`app/workers/lifecycle.py`)
  - Czyta/pisze: `jobs`
  - Operacje: `new/active/stale/expired/unreachable`, repost markers

- **Availability worker** (`app/workers/availability.py`)
  - Czyta: `jobs` (oferty do weryfikacji)
  - Pisze: `jobs.availability_status`, `last_verified_at`, `verification_failures`

- **Market metrics worker** (`app/workers/market_metrics.py`)
  - Czyta: `jobs`, `job_sources`
  - Pisze: `market_daily_stats`, `market_daily_stats_segments`

### Discovery workers
- `run_careers_discovery` (`app/workers/discovery/careers_crawler.py`)
- `run_ats_guessing` (`app/workers/discovery/ats_guessing.py`)

### Utility/backfill workers (internal ops)
- compliance backfill: `POST /internal/backfill-compliance`
- salary backfill: `POST /internal/backfill-salary`

---

## 4) APIs

### Public API
- `GET /health` – liveness
- `GET /ready` – readiness
- `GET /jobs` – lista ofert (filtry)
- `GET /jobs/feed` – feed (visible jobs, compliance threshold)
- `GET /jobs/stats/compliance-7d` – agregaty compliance 7d

### Internal API (operacje i audit)
- `POST /internal/tick` – uruchamia runtime pipeline
- `GET /internal/audit` – panel audit HTML
- `GET /internal/audit/jobs` – listing + statystyki audit
- `GET /internal/audit/filters` – słowniki filtrów + dynamiczne source
- `GET /internal/audit/stats/company` – compliance ratio per firma
- `GET /internal/audit/stats/source-7d` – compliance ratio per source (7d)
- `POST /internal/audit/tick-dev` – tick dev/debug
- `POST /internal/backfill-compliance` – worker backfill compliance
- `POST /internal/backfill-salary` – worker backfill salary

---

## Minimalny obraz całości

`External ATS -> Adapters -> Ingestion Worker -> jobs/job_sources/compliance_reports -> Lifecycle+Availability -> Market Metrics -> Public/Internal APIs`
