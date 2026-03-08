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
- [x] Curated employer ATS ingestion (Greenhouse)
- [x] Source-specific normalization and policy signal stages
- [x] Legacy source runtime modules (`remotive`, `remoteok`, `weworkremotely`) removed

### Data platform
- [x] PostgreSQL schema with migration files (`jobs`, `companies`)
- [x] SQLAlchemy Core storage backend
- [x] `DB_MODE=standard` and `DB_MODE=cloudsql`
- [x] Idempotent upsert and lifecycle timestamps

### Compliance and lifecycle
- [x] Remote/geo class normalization
- [x] Compliance status + scoring resolver
- [x] Startup backfill for missing compliance metadata
- [x] Availability and lifecycle workers (`new|active|stale|expired|unreachable`)

### API and audit
- [x] Public read API: `/jobs`, `/jobs/feed`
- [x] Public 7-day compliance snapshot endpoint: `/jobs/stats/compliance-7d`
- [x] Feed threshold: `min_compliance_score=80`
- [x] Internal tick endpoint with text/json formatting
- [x] Internal audit panel and filterable audit API
- [x] Internal audit aggregate stats endpoints (`/internal/audit/stats/company`, `/internal/audit/stats/source-7d`)
- [x] Audit filter registry extended with dynamic source dropdown values

### Ops
- [x] Cloud Run deployment via Terraform (`infra/gcp/dev`, `infra/gcp/prod`)
- [x] Cloud Scheduler trigger for `/internal/tick` in production
- [x] CI test workflow with PostgreSQL service
- [x] Runtime-aware logging (text local, JSON in containers)

---

## Next Priorities

### P1 – Source strategy
- [ ] Finalize explicit activation policy for adapters present in code but disabled in registry

### P2 – Company data maturity
- [ ] Add operational workflows for curated `companies` maintenance (ATS slug hygiene, activation lifecycle)
- [ ] Connect company signal scoring pipeline into production runtime decisions

### P3 – DB and migration hardening
- [ ] Introduce explicit migration tooling (Alembic or equivalent)
- [ ] Tune indexes for feed/audit/lifecycle query patterns
- [ ] Add automated post-deploy smoke checks

### P4 – Observability
- [ ] Add scheduler/tick failure alerting
- [ ] Add trend dashboards for per-source quality drift and rejection reasons

---

## Future Direction

- Controlled company self-publishing workflows (manual/compliance-first)
- Richer structured metadata once source quality is stable
- Policy reason taxonomy expansion and review tooling for borderline offers
