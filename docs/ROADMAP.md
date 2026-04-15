# OpenJobsEU Roadmap

## Scope

OpenJobsEU remains a compliance-first aggregation backend for EU-relevant remote jobs.

Non-goals remain unchanged:
- no scraping of closed/protected platforms
- no candidate accounts/tracking layer
- no automated posting to third-party platforms

---

## Delivered Baseline

### Runtime and ingestion
- [x] Tick-based runtime with local and pipeline modes
- [x] Active handler: `employer_ing`
- [x] Curated employer ATS ingestion via the ATS adapter registry
- [x] Source-specific normalization and policy signal stages
- [x] Legacy source runtime modules (`remotive`, `remoteok`, `weworkremotely`) removed

### Data platform
- [x] PostgreSQL schema managed with Alembic migrations
- [x] SQLAlchemy Core storage backend
- [x] `DB_MODE=standard` and `DB_MODE=cloudsql`
- [x] Idempotent upsert and lifecycle timestamps

### Compliance and lifecycle
- [x] Remote/geo class normalization
- [x] Compliance status + scoring resolver
- [x] Startup backfill for missing compliance metadata
- [x] Availability and lifecycle workers (`new|active|stale|expired|unreachable`)

### API and audit
- [x] Private runtime read APIs: `/jobs`, `/companies`, `/jobs/stats/compliance-7d`
- [x] Public static dataset/feed export via `feed.json`
- [x] Feed threshold: `min_compliance_score=80`
- [x] Internal tick endpoint with text/json formatting
- [x] Internal audit panel and filterable audit API
- [x] Internal audit aggregate stats endpoints (`/internal/audit/stats/company`, `/internal/audit/stats/source-7d`)
- [x] Audit filter registry extended with dynamic source dropdown values
- [x] UI/UX decoupling from API (100% static frontend export)

### Ops
- [x] Cloud Run deployment via Terraform (`infra/gcp/dev`, `infra/gcp/prod`)
- [x] Cloud Scheduler trigger for `/internal/tick` in production
- [x] CI test workflow with PostgreSQL service
- [x] Runtime-aware logging (text local, JSON in containers)
- [x] Reorganized ATS adapters into `app/adapters/ats/` structure
- [x] Cloud Tasks for robust async execution (backfills, async tick execution, staggered discovery phases)
- [x] OIDC authentication for M2M communication (Scheduler, Tasks)
- [x] Modular Monolith routing groups for strict access control
- [x] Strict OIDC audience validation for Cloud Tasks execution
- [x] Zero-compute public feed generation (GCS static export)
- [x] Adaptive time-budgeting for serverless workers

---

## Next Priorities

### P1 – Source strategy
- [x] Finalize explicit activation policy for adapters present in code but disabled in registry

### P2 – Company data maturity
- [x] Add operational workflows for curated `companies` maintenance (ATS slug hygiene, activation lifecycle)
- [x] Connect company signal scoring pipeline into production runtime decisions

### P3 – DB and migration hardening
- [x] Introduce explicit migration tooling (Alembic or equivalent)
- [x] Tune indexes for feed/audit/lifecycle query patterns (e.g., covering compound indexes, `GROUPING SETS`)
- [x] Add automated post-deploy smoke checks

### P4 – Observability
- [x] Add scheduler/tick failure alerting
- [x] Add trend dashboards for per-source quality drift and rejection reasons

### P5 – Discovery maturity
- [x] Multi-stage ATS discovery pipeline (`company-sources`, `careers`, `ats-reverse`, `guess`, `dorking`, `dorking-crt`, `slug_harvest`, promotion)
- [x] Introduce `discovered_slugs` as a staging layer before promotion to `company_ats`
- [x] Add `slug_harvest` worker with robots-aware shallow crawl and confidence-based slug extraction
- [x] Teamtailor discovery candidate flow with `needs_token` status (manual token binding instead of false auto-promotion)
- [x] Internal discovery UI endpoint for slug candidates (`/internal/discovery/slug-candidates`)

---

## Future Direction

- Controlled company self-publishing workflows (manual/compliance-first)
- Richer structured metadata once source quality is stable
- Policy reason taxonomy expansion and review tooling for borderline offers

### Planned features

- public dataset API
- ~~labour market analytics~~ — static segment export (`market-segments.json`) + breakdown UI delivered; time-series API and employment-type schema expansion remain
- ~~commercial API plans~~ — `/api/v1/` tier delivered: API key auth (SHA-256, `ojeu_<32chars>` format), three tiers (`free`/`pro`/`enterprise`), PostgreSQL-backed daily rate limiting
