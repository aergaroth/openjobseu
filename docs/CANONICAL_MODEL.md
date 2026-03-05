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

## Job Metadata (implemented)

- **title**
- **company_name**
- **description**

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

Feed usage:
- `/jobs/feed` returns visible jobs with `compliance_score >= 80`

---

## Lifecycle and Tracking (implemented)

- **status**:
  `new | active | stale | expired | unreachable`
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
- `unreachable` -> temporary access failure

Visible jobs for API/feed: `new`, `active`.

---

## Company Linkage (implemented)

- **company_id**: nullable UUID FK to `companies.company_id`

Usage:
- `employer_ing` writes jobs with explicit `company_id`
- legacy/other sources may leave `company_id` null

---

## Persistence Notes

- earliest `first_seen_at` is preserved on conflict upsert
- `last_seen_at` is refreshed on each successful upsert
- `remote_class` and `geo_class` are normalized at write-time and backfilled when missing
- compliance resolver updates `compliance_status` and `compliance_score`
- availability/lifecycle workers update `status`, `last_verified_at`, `verification_failures`

---

## Intentionally Deferred Fields

The runtime does not currently persist enriched fields such as:
- employment type / seniority / role category
- compensation ranges
- timezone or detailed country restrictions

These can be added in later model revisions once source reliability and policy contracts are defined.

---

## Adapter vs Normalization Contract

Adapters:
- fetch source payloads
- handle transport and source-specific wire formats
- do not persist

Normalization:
- validates required fields
- maps payloads to canonical fields
- sanitizes URLs/locations
- may reject malformed or clearly out-of-scope records
