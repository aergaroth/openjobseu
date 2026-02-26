# System Architecture – OpenJobsEU

## Overview

OpenJobsEU is an open-source, compliance-first platform for aggregating legally accessible, EU-focused remote job offers.

The system is designed as a backend-oriented, production-grade pipeline with a strong emphasis on:
- clear separation of concerns
- data freshness and lifecycle correctness
- operational transparency
- cloud-native deployment

User-facing functionality is intentionally minimal and strictly read-only.

---

## High-Level Architecture

![Architecture diagram](./architecture.png)


The system operates as a periodic **tick-based pipeline**:

External Sources -> Ingestion -> Normalization -> Storage -> Compliance Resolution -> Post-ingestion -> Read API -> Consumers

This model ensures predictable behavior, resilience to partial failures, and clear operational boundaries.

> In production (Cloud Run), OpenJobsEU runs in prod mode by default.
> Development-only local ingestion requires explicitly setting ```INGESTION_MODE=local```

> Logging format is determined by runtime mode. Local development uses text logs, while containerized deployments emit 
> structured JSON logs.

> Database backend is selected via `DB_MODE`:
> - `standard` -> PostgreSQL via `DATABASE_URL` (`postgresql+psycopg://...`)
> - `cloudsql` -> Cloud SQL Python Connector (`pg8000`, IAM auth)

---

## Core Components

### External Job Sources

Legally accessible, public job data sources such as:
- public RSS feeds
- public JSON APIs

No scraping, authentication bypassing, or automated interactions are performed.

---

### Ingestion Adapters

Each source is integrated via a dedicated ingestion adapter responsible for:
- fetching raw job data
- handling source-specific formats
- emitting raw job entries

Adapters are isolated so failures in one source do not affect others.

---

### Normalization Layer

The normalization layer converts raw job entries into a single **canonical job model**.

Responsibilities:
- enforce required fields
- apply source-specific heuristics safely
- reject malformed or out-of-scope source entries
- produce source-agnostic job records

Normalization does not compute final compliance score/status.

---

### Job Store

The job store is the system’s single source of truth.

Responsibilities:
- persist normalized job data
- track lifecycle-related timestamps
- support idempotent upserts

Current runtime uses SQLAlchemy Core with PostgreSQL-compatible SQL.
It supports standard PostgreSQL URLs and Cloud SQL connector mode.

---

### Compliance Resolution Layer

After ingestion, the pipeline runs deterministic compliance resolution:
- derive/normalize `remote_class`
- derive/normalize `geo_class`
- compute `compliance_status` (`approved` / `review` / `rejected`)
- compute `compliance_score` (0-100)

On app startup, existing rows missing compliance metadata are batch-backfilled.

---

### Availability & Lifecycle

Background workers handle:
- periodic availability verification of job URLs
- lifecycle transitions (NEW → ACTIVE → STALE → EXPIRED / UNREACHABLE)

These processes are asynchronous and do not block ingestion or API access.

---

### Read API

The Read API exposes job data in a strictly read-only manner.

Key properties:
- stateless
- cache-friendly
- contract-stable

Endpoints:
- GET /jobs
- GET /jobs/feed

`/jobs/feed` is additionally filtered by `min_compliance_score=80`.

Only visible jobs (NEW and ACTIVE) are exposed to consumers.

Internal operational endpoints:
- POST /internal/tick
- GET /internal/audit
- GET /internal/audit/jobs
- POST /internal/audit/tick-dev

---

### Frontend & Consumers

Consumers include:
- a minimal reference frontend
- external aggregators
- automated systems

All consumers interact exclusively via the Read API or public feed.

---

## Execution Model

The entire system is executed via a periodic **scheduler-triggered tick**:

1. Ingestion phase
2. Compliance resolution phase
3. Post-ingestion processing
4. Availability checks (inside post-ingestion)
5. Lifecycle transitions (inside post-ingestion)

This design avoids long-running workers and ensures deterministic execution.

---

## Observability

Observability is provided via:
- structured application logs
- explicit ingestion phase logging
- runtime tick metrics (duration, per-source ingestion counts, policy counters, remote-model counters)
- compliance resolution summaries
- health and readiness endpoints

More advanced metrics and alerting are planned.

The repository also includes a DB/runtime smoke script: `scripts/db_smoke_check.py`.

The smoke check validates:
- application health endpoint
- successful tick execution
- database accessibility and integrity
- job_id uniqueness
- basic feed consistency

When integrated in CI/CD, any failure should block deployment and require investigation.


---

## Compliance Boundaries

OpenJobsEU explicitly avoids:
- scraping closed platforms
- user tracking or profiling
- automated redistribution to third parties

All processing is limited to legally accessible data sources.
