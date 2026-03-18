# Changelog

## [Unreleased] – develop → main (initial release)

### Added

#### Core platform
- Tick-based ingestion runtime (`POST /internal/tick?limit=X`) with text/JSON output formatting and pagination
- Support for batched Full Sync (`incremental=false`) via `scripts/tick-full-sync.sh` to gracefully bypass Cloud Run timeouts
- ATS adapter layer (`app/adapters/ats/`): `GreenhouseAdapter`, `LeverAdapter`, with `probe_jobs` support
- `PersonioAdapter` utilizing a robust streaming XML pull-parser (memory-safe, 10MB limit)
- Discovery pipeline: ATS guessing worker, ATS probe worker, careers-page crawler
- Async Background Tasks API (`/internal/tasks/*`) for long-running operations (backfills, discovery pipelines)

#### Compliance & classification
- Remote/geo classifiers (`geo`, `hard_geo`, `remote`) with EU-relevance scoring
- Enhanced Geo-classifier with direct mapping of EOG countries and major European cities from job titles and scope
- Compliance engine and resolver with scoring and startup backfill utilities
- Salary parser and structured salary model with currency normalisation
- HTML to Markdown description normalization engine (lists, bold, italics, links, blockquotes, headers)

#### Job lifecycle
- Job identity and deduplication layer
- Lifecycle transitions (`new → active → stale → expired → unreachable`)
- Availability worker and lifecycle worker

#### API
- Public endpoints: `GET /jobs`, `GET /jobs/feed`, `GET /jobs/stats/compliance-7d`
- Internal/ops endpoints: `POST /internal/tick`, `GET /internal/audit`, audit stats endpoints
- Feed threshold: `min_compliance_score=80`, cached at `max-age=300`

#### Storage
- PostgreSQL schema with 16 incremental SQL migration files
- SQLAlchemy Core backend; supports `DB_MODE=standard` and `DB_MODE=cloudsql`
- Repositories for jobs, companies, audit, compliance, availability, and discovery

#### Ops & CI/CD
- GitHub Actions workflows: `dev_flow.yml`, `prod_flow.yml`, `terraform-plan.yml`
- Terraform infrastructure for GCP (`infra/gcp/dev`, `infra/gcp/prod`) with Cloud Run and Cloud Scheduler
- Runtime-aware structured logging (text locally, JSON in containers)
- Full test suite (`validator/tests/`) strictly blocking unmocked external HTTP requests to prevent test hangs
- Heavily optimized Pytest DB fixtures (replacing structural `TRUNCATE CASCADE` with ultra-fast `DELETE` sweeps)
