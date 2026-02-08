# Canonical Job Model – OpenJobsEU

The canonical job model defines a single, source-agnostic representation of job offers within OpenJobsEU.

All incoming job data is normalized to this model to ensure consistent processing,
storage, and querying across different sources.

---

## Core Identifiers (implemented)

- **job_id**: globally unique identifier (string, source-scoped, stable)
- **source**: identifier of the original data source (e.g. `weworkremotely`, `remotive`, `remoteok`)
- **source_job_id**: job identifier in the source system
- **source_url**: original job posting URL

---

## Job Metadata (implemented)

- **title**: job title
- **company_name**: company or organization name
- **description**: normalized job description (plain text)

---

## Location & Scope (implemented)

- **remote**: boolean (must be `true` for inclusion)
- **remote_scope**: source-provided scope, preserved verbatim 
  Examples:
  - `EU-wide`
  - `Worldwide`
  - `Europe`
  - `Europe, Canada, South Africa`

Normalization logic may reject jobs that do not match OpenJobsEU policy
(e.g. non-EU–restricted roles).

---

## Lifecycle & Tracking (implemented)

- **status**:
  `new | active | stale | expired | unreachable`

- **first_seen_at**: timestamp of first successful ingestion
- **last_seen_at**: timestamp of last successful ingestion
- **last_verified_at**: timestamp of last successful availability check
- **verification_failures**: number of consecutive availability check failures

### Status semantics

- **NEW** – freshly discovered job (first 24h after `first_seen_at`)
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
- ingestion and normalization do not modify lifecycle state beyond initial creation

---

## Planned near-term extension

### Source posting date (planned)

- **posted_at**: original publication date provided by the source (if available)

Notes:
- This field will be used to improve freshness handling and deduplication
- Lifecycle logic will continue to rely on `first_seen_at` and verification checks
- `posted_at` will never override lifecycle state directly

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

## Ingestion & Normalization Contract

### Adapters
Each ingestion adapter must:
- fetch raw job data from a single source
- expose source identifier and source job ID
- return unmodified source payloads

Adapters **must not**:
- apply heuristics
- enforce OpenJobsEU policy
- modify lifecycle state
- persist data

### Normalization
Normalization is responsible for:
- validating required fields
- enforcing OpenJobsEU inclusion policy
- mapping raw payloads to the canonical job model
- rejecting non-compliant job offers

Normalization is source-specific, deterministic, and covered by automated tests.
