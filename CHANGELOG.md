# Changelog

## [Unreleased] – develop → main (initial release)

### Added

#### Core platform
- Tick-based ingestion runtime (`POST /internal/tick`) with text/JSON output formatting
- ATS adapter layer (`app/adapters/ats/`): `GreenhouseAdapter`, `LeverAdapter`, with `probe_jobs` support
- Discovery pipeline: ATS guessing worker, ATS probe worker, careers-page crawler

#### Compliance & classification
- Remote/geo classifiers (`geo`, `hard_geo`, `remote`) with EU-relevance scoring
- Compliance engine and resolver with scoring and startup backfill utilities
- Salary parser and structured salary model with currency normalisation

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
- Full test suite (`validator/tests/`) covering adapters, compliance, pipeline, storage, and salary parsing
