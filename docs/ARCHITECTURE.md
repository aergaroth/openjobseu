# System Architecture – OpenJobsEU

## Overview

OpenJobsEU is a backend-first, compliance-focused pipeline for aggregating legally accessible remote job offers with EU relevance signals.

The runtime is intentionally read-only on the public side and operationally explicit on the internal side.

---

## High-Level Flow

![Architecture diagram](./architecture.png)

Pipeline mode flow:

External Sources -> Ingestion Handlers -> Source Normalization + Policy Signals -> DB Upsert -> Compliance Resolution -> Post-Ingestion Workers -> Read APIs

---

## Runtime Modes

- `INGESTION_MODE=local`
  - runs `app.workers.tick.run_tick`
  - reads `ingestion/sources/example_jobs.json`
  - runs post-ingestion workers
- any non-local mode (`prod`, `dev`, etc.)
  - runs `app.workers.tick_pipeline.run_tick_pipeline`
  - executes configured ingestion handlers
  - runs compliance resolution + post-ingestion

Handler selection:
- if `INGESTION_SOURCES` is set, its comma-separated values are used
- otherwise all handlers from `app/workers/ingestion/registry.py` are used

Current active handlers in registry:
- `remotive`
- `employer_ing`

---

## Ingestion Layer

### `remotive`

Runtime path:
- adapter: `ingestion/adapters/remotive_api.py`
- normalization: `app/workers/normalization/remotive.py`
- policy tagging: `app/workers/policy/v1.py`

### `employer_ing`

Runtime path:
- loads active ATS companies from `companies` table (`is_active=true`, `ats_provider`, `ats_slug`)
- currently supports `ats_provider=greenhouse`
- adapter: `ingestion/adapters/greenhouse_api.py`
- normalization: `app/workers/normalization/greenhouse.py`
- policy tagging: `app/workers/policy/v3/apply_policy_v3.py`

`employer_ing` can hard-skip records with `geo_restriction_hard` signals before DB upsert.

### Present in code but disabled in registry

- `remoteok`
- `weworkremotely`

Those adapters/workers exist but are commented out in the default ingestion registry.

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

After ingestion, compliance resolution (`app/workers/compliance_resolution.py`) computes:
- `compliance_status`: `approved | review | rejected`
- `compliance_score`: `0..100`

On startup, missing class/compliance fields are backfilled in batches.

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

Feed behavior:
- visible jobs only (`new`, `active`)
- minimum compliance score: `80`
- cache header: `Cache-Control: public, max-age=300`

Internal endpoints:
- `POST /internal/tick` (`format=auto|text|json`)
- `GET /internal/audit`
- `GET /internal/audit/jobs`
- `GET /internal/audit/filters`
- `POST /internal/audit/tick-dev`

---

## Logging and Metrics

Logging mode:
- text formatter in local runtime (`APP_RUNTIME=local` or non-container)
- JSON formatter in container/cloud runtime

Tick payload/summary includes:
- per-source fetch/persist/skip counters
- policy rejection counters
- remote model counters
- timing metrics

---

## Deployment Shape

Infrastructure is managed with Terraform in split environments:
- `infra/gcp/dev`
- `infra/gcp/prod`

Production scheduler triggers `POST /internal/tick` every 15 minutes.
