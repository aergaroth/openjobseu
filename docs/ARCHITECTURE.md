# System Architecture – OpenJobsEU

## Overview

OpenJobsEU is an open-source, compliance-first platform for aggregating legally accessible remote job offers within the European Union.

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

External Sources → Ingestion → Normalization → Storage → Availability & Lifecycle → Read API → Consumers

This model ensures predictable behavior, resilience to partial failures, and clear operational boundaries.

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
- reject non-compliant or out-of-scope jobs
- produce source-agnostic job records

Normalization is the primary policy boundary of the system.

---

### Job Store

The job store is the system’s single source of truth.

Responsibilities:
- persist normalized job data
- track lifecycle-related timestamps
- support idempotent upserts

The current implementation uses SQLite, with the design allowing replacement by a higher-level database engine in the future.

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

Only visible jobs (NEW and ACTIVE) are exposed to consumers.

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
2. Post-ingestion processing
3. Availability checks
4. Lifecycle transitions

This design avoids long-running workers and ensures deterministic execution.

---

## Observability

Observability is provided via:
- structured application logs
- explicit ingestion phase logging
- health and readiness endpoints

More advanced metrics and alerting are planned.

---

## Compliance Boundaries

OpenJobsEU explicitly avoids:
- scraping closed platforms
- user tracking or profiling
- automated redistribution to third parties

All processing is limited to legally accessible data sources.

