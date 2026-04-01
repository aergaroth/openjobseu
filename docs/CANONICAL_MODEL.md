# Canonical Job Model – OpenJobsEU

The canonical model is the persisted shape of job offers in `jobs` table after normalization and upsert.

---

## Core Identifiers (implemented)

- **job_id**: globally unique identifier, source-scoped
- **source**: source identifier (example: `greenhouse:{board_token}`)
- **source_job_id**: source-native identifier
- **source_url**: source posting URL (sanitized)

Notes:
- historical rows may also contain `remotive`, `remoteok`, or `weworkremotely` source values
- current default ingestion registry runs `employer_ing` only

---

## Internal Identifiers & Versioning (implemented)

These fields are used for data integrity, deduplication, and tracking changes.

- **job_uid**: A stable identifier for a job role at a company (company + title + location).
- **job_fingerprint**: A hash of the job's core content to detect changes.
- **source_schema_hash**: A hash of the raw data from the source to detect schema changes.

---

## Job Metadata (implemented)

- **title**
- **company_name**
- **description**
- **source_department**

---

## Location and Remote Signals (implemented)

- **remote_source_flag**: source-level remote indicator (bool)
- **remote_scope**: source-provided geographic/scope text

`remote_source_flag` can differ by source quality; final policy/compliance decision is resolved downstream.

---

## Classification and Compliance (implemented)

- **remote_class**:
  `remote_only | remote_region_locked | remote_optional | non_remote | unknown`

Historical alias still present in some data paths/metrics:
- `remote_but_geo_restricted` (legacy alias for `remote_region_locked`)

- **geo_class**:
  `eu_member_state | eu_explicit | eu_region | uk | non_eu | unknown`

- **compliance_status**:
  `approved | review | rejected`

- **compliance_score**:
  integer `0..100`

- **policy_version**:
  string (e.g., `v4.ab12cd3`)


- **job_family**: `software_development | data_science | design | ...`
- **job_role**: `engineer | developer | product_manager | ...`
- **seniority**: `junior | senior | staff | manager | ...`
- **specialization**: `backend | frontend | devops | ...`
- **job_quality_score**: integer `0..100`

Feed usage:
- `feed.json` (static GCS export) returns visible jobs with `compliance_score >= 80`

---

## Lifecycle and Tracking (implemented)

- **status**:
  `new | active | stale | expired`
- **availability_status**:
  `active | expired | unreachable`
- **first_seen_at**
- **last_seen_at**
- **last_verified_at**
- **verification_failures**
- **updated_at**

Status semantics:
- `new` -> first 24h from `first_seen_at`
- `active` -> healthy/visible
- `stale` -> verification outdated
- `expired` -> unavailable or aged-out by rules

Visible jobs for API/feed: `new`, `active`.

---

## Company Linkage (implemented)

- **company_id**: nullable UUID FK to `companies.company_id`

Usage:
- `employer_ing` writes jobs with explicit `company_id`
- legacy/other sources may leave `company_id` null

---

## Salary and Compensation (implemented)

- **salary_min**: integer
- **salary_max**: integer
- **salary_currency**: `EUR | USD | GBP | PLN`
- **salary_period**: `year | month | hour | day`
- **salary_source**: `structured | regex_v3`
- **salary_min_eur**: integer (normalized to EUR)
- **salary_max_eur**: integer (normalized to EUR)
- **salary_transparency_status**: `disclosed | transparent_statement | not_disclosed | unknown`

`salary_source` indicates the extraction method:
- `structured`: Extracted from dedicated ATS fields (e.g., `salary_range` object).
- `regex_v3`: Extracted from the job description text using regular expressions.

`salary_transparency_status` indicates the level of salary disclosure:
- `disclosed`: Salary figures detected.
- `transparent_statement`: No figures, but text promises disclosure.
- `not_disclosed`: No salary information found.

---

## Persistence Notes

- earliest `first_seen_at` is preserved on conflict upsert
- `last_seen_at` is refreshed on each successful upsert
- `remote_class` and `geo_class` are normalized at write-time and backfilled when missing
- compliance resolver updates `compliance_status` and `compliance_score`
- availability/lifecycle workers update `status`, `availability_status`, `last_verified_at`, `verification_failures`

---

## Intentionally Deferred Fields

The runtime does not currently persist enriched fields such as:
- employment type (contract/perm)
- timezone or detailed country restrictions

These can be added in later model revisions once source reliability and policy contracts are defined.

---

## Adapter vs Normalization Contract

Adapters:
- located in `app/adapters/ats/`
- fetch source payloads
- handle transport and source-specific wire formats
- do not persist

Normalization:
- validates required fields
- maps payloads to canonical fields
- sanitizes URLs/locations
- may reject malformed or clearly out-of-scope records
