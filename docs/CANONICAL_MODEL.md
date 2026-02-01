# Canonical Job Model – OpenJobsEU

The canonical job model defines a single, source-agnostic representation of job offers within OpenJobsEU.

All ingestion adapters normalize incoming data to this model to ensure consistent processing, storage, and querying across different sources.

---

## Core Identifiers (implemented)

- **job_id**: globally unique identifier (string, source-scoped)
- **source**: identifier of the original data source
- **source_job_id**: job identifier in the source system
- **source_url**: original job posting URL

---

## Job Metadata (implemented)

- **title**: job title
- **company_name**: company or organization name
- **description**: normalized job description (plain text)

---

## Location & Scope (implemented)

- **remote**: boolean (must be true for inclusion)
- **remote_scope**: EU-wide | selected_countries

---

## Lifecycle & Tracking (implemented)

- **status**:
  `new | active | stale | expired | unreachable`

- **first_seen_at**: timestamp of first ingestion
- **last_seen_at**: timestamp of last successful ingestion
- **last_verified_at**: timestamp of last successful availability check
- **verification_failures**: number of consecutive availability check failures

### Status semantics

- **NEW** – freshly discovered job (first 24h after first_seen_at)
- **ACTIVE** – verified and visible job
- **STALE** – job not verified within a defined time window
- **EXPIRED** – job confirmed unavailable or outdated
- **UNREACHABLE** – temporarily unreachable job source

From an API consumer perspective, **NEW and ACTIVE jobs are treated as visible**.

---

## Persistence notes

- `first_seen_at` is set only once, on initial ingestion
- `last_seen_at` is updated on each successful ingestion of the same job
- `last_verified_at` is updated only by the availability checker
- ingestion adapters do not modify lifecycle state beyond initial creation

---

## Planned extensions (not yet implemented)

The following fields are part of the long-term canonical model but are not yet populated by the current runtime:

### Job attributes
- employment_type
- seniority
- role_category
- tech_tags

### Compensation
- salary_min
- salary_max
- salary_currency
- salary_period

### Constraints
- timezone_requirements
- country_restrictions

These fields are intentionally deferred to keep the initial implementation focused and minimal.

---

## Ingestion Adapter Contract

Each ingestion adapter must:
- fetch job data from a single source
- map source fields to the canonical job model
- provide source identifier and source job ID
- set initial lifecycle state (`new`) on first ingestion

Adapters are not responsible for availability verification or lifecycle transitions.
