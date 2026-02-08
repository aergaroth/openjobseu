# System Architecture – OpenJobsEU

## Overview

OpenJobsEU is an open-source, compliance-first platform for aggregating **legally accessible, EU-wide remote job offers**.

The system is designed as a **backend-first ingestion platform**, with strong emphasis on:
- clear separation of responsibilities
- correctness and data freshness
- explicit lifecycle management
- infrastructure automation
- operational transparency

User-facing features are intentionally minimal and treated as **secondary consumers** of the data.

---

## High-Level Architecture

![Architecture diagram](./architecture.png)

At runtime, OpenJobsEU operates as a **tick-based ingestion system**:

**dispatcher → ingestion → normalization → persistence → availability → lifecycle → read API**

The system is intentionally **pull-based and stateless** between ticks.

Availability checks and lifecycle transitions are executed **after ingestion** and do not block data fetching.

---

## Tick Dispatcher

The entry point for all background work is:

```
POST /internal/tick
```

The dispatcher:
- reads active ingestion sources from environment configuration
- invokes each source independently
- aggregates ingestion results
- triggers post-ingestion processing

This design ensures:
- isolation between sources
- predictable execution order
- safe extension with new adapters

---

## Ingestion Sources

Each external job source is integrated as a **fetch-only adapter**, responsible solely for:
- retrieving raw data
- handling source-specific formats
- returning unmodified payloads

Adapters **do not**:
- apply heuristics
- perform normalization
- persist data
- modify lifecycle state

Currently implemented sources include:
- WeWorkRemotely (RSS)
- Remotive (public API)
- RemoteOK (public API)

---

## Normalization Layer

Normalization is handled by **source-specific normalizers**, executed immediately after fetching.

Responsibilities:
- validate required fields
- enforce OpenJobsEU inclusion rules (EU-wide, remote-only)
- map raw payloads to the canonical job model
- reject jobs that do not meet project criteria

Normalization is:
- explicit
- deterministic
- fully test-covered

This layer is the **policy boundary** of the system.

---

## Job Store

The job store is the system’s single source of truth.

Responsibilities:
- persist normalized job records
- ensure idempotent upserts
- track lifecycle and verification timestamps

Current backend:
- SQLite (sufficient for early-stage and development)

The storage layer is designed to be **replaceable** without changes to ingestion or normalization logic.

---

## Availability Checker

After ingestion, a background worker:
- periodically verifies job URLs via HTTP
- interprets response codes and network failures
- updates availability-related fields

The checker prioritizes:
- correctness over volume
- freshness over completeness

Availability results directly influence lifecycle transitions.

---

## Job Lifecycle

Each job progresses through a defined lifecycle:

- **NEW** – freshly discovered job
- **ACTIVE** – verified and visible
- **STALE** – not verified within the expected window
- **EXPIRED** – confirmed unavailable or outdated

From an API consumer perspective:
- **NEW** and **ACTIVE** jobs are considered *visible*

Lifecycle transitions are deterministic and rule-based.

---

## Read API

The Read API exposes job data in a **read-only, consumer-safe** manner.

### Query API

```
GET /jobs
```

Query parameters:
- `status`: visible | new | active | stale | expired
- `limit`: default 20
- `offset`: default 0

Example:
```
GET /jobs?status=visible
```

---

### Public Job Feed

In addition to the query API, OpenJobsEU exposes a **stable public JSON feed**:

```
GET /jobs/feed
```

The feed:
- returns all visible jobs (NEW + ACTIVE)
- does not support filtering or pagination
- is cache-friendly and contract-stable

It is intended for:
- simple frontends
- external aggregators
- automated consumers

---

## Infrastructure

OpenJobsEU follows cloud-native infrastructure principles:
- containerized runtime
- Infrastructure as Code (Terraform)
- CI pipelines with automated tests
- environment-driven configuration

Current deployment target:
- Google Cloud Run

The system is designed to remain **cloud-provider portable**.

---

## Observability

Observability is provided via:
- structured ingestion logs
- unified ingestion event logging
- health and readiness endpoints
- Cloud Run and Scheduler execution logs

Metrics and alerting are intentionally deferred until ingestion behavior stabilizes.

---

## Compliance and Legal Boundaries

OpenJobsEU explicitly avoids:
- scraping closed or protected platforms
- bypassing access controls
- automating third-party interactions
- redistributing proprietary content

All data originates from:
- legally accessible public sources
- explicit, source-provided APIs

Compliance is treated as a **first-class architectural constraint**.
