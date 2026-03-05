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

- Runtime entrypoint: `app.workers.tick_pipeline.run_tick_pipeline`
- Tick pipeline orchestration:
  - runs `run_employer_ingestion()`
  - runs `run_post_ingestion()`
- Ingestion worker is single-source and ATS-backed (`employer_ing`)

---

## Ingestion Layer

### `employer_ing`

Runtime path:
- loads active ATS companies from `companies` table (`is_active=true`, `ats_provider`, `ats_slug`)
- adapters resolved via `app/ats/registry.py`
- current adapter implementations:
  - `app/ats/greenhouse.py`
  - `app/ats/lever.py` (inactive)
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
