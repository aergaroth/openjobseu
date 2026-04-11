# Data Sources – OpenJobsEU

OpenJobsEU integrates only legally accessible, read-only sources.

Every record goes through:
- ATS adapter fetch
- adapter-level normalization
- compliance policy (`apply_policy`)
- canonical upsert
- post-ingestion lifecycle and availability

---

## Active Ingestion Path

### Employer ATS Ingestion (`employer_ing`)

- **Type:** Curated company list + ATS API fetch
- **Worker:** `app/workers/ingestion/employer.py`
- **Adapter registry:** `app/adapters/ats/registry.py`
- **Current ATS support:** Greenhouse, Lever, Workable, Ashby, Personio, Recruitee, SmartRecruiters, JobAdder, Teamtailor.

Input set is loaded from `companies` rows where:
- `is_active = true`
- `ats_provider IS NOT NULL`
- `ats_slug IS NOT NULL`

Current provider behavior:
- supported provider -> fetch + normalize + policy + persist
- unsupported/inactive provider -> skipped with ingestion metrics

`geo_restriction_hard` offers are flagged in metrics and persisted with a rejected status to enable broader market analytics.

---

## Source Integration Contract

Adapters:
- fetch ATS payloads
- normalize source records to canonical shape
- do not persist data directly

Ingestion worker:
- runs policy engine
- aggregates observability metrics
- writes canonical records to DB

Post-ingestion workers:
- run availability checks
- apply lifecycle transitions
- export static JSON feed to Cloud Storage

---

## Onboarding Criteria for New ATS Providers

A provider is enabled only after:
- legal accessibility/reuse confirmation
- stable payload quality
- deterministic normalization and policy behavior
- test coverage for adapter + ingestion integration

Scraping closed/protected platforms remains out of scope.
