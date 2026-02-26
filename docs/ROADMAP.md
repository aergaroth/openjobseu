# OpenJobsEU Roadmap

## Project scope

OpenJobsEU is an open-source, compliance-first platform for aggregating EU-focused remote job offers.

The project is developed incrementally, with a strong focus on:
- clean domain modeling
- operational correctness
- real cloud deployment

It is not a demo or mock system — all components are designed to run in production infrastructure.

---

## Explicit non-goals

- Scraping closed or protected job boards
- Automated posting to third-party platforms
- Candidate accounts, profiles, or tracking

---

## MVP v1 — DONE

### A1 – Ingestion
- [x] Canonical job data model
- [x] Local JSON ingestion (dev)
- [x] RSS ingestion (WeWorkRemotely)
- [x] Public API ingestion (Remotive, RemoteOK)
- [x] Source-specific normalization with tests

### A2 – Persistence
- [x] SQLAlchemy Core storage layer
- [x] PostgreSQL runtime backend (`DB_MODE=standard`)
- [x] Idempotent job upsert
- [x] First-seen and last-seen tracking

### A3 – Availability checking
- [x] HTTP-based availability checks
- [x] Failure tracking and retries

### A4 – Lifecycle management
- [x] NEW / ACTIVE / STALE / EXPIRED / UNREACHABLE states
- [x] Time-based transitions
- [x] Failure-based expiration

### A5 – Read API
- [x] GET /jobs endpoint
- [x] Status filtering
- [x] Visible jobs abstraction (new + active)

### A6 – Distribution & consumption
- [x] Public JSON feed (`/jobs/feed`)
- [x] Stable, cache-friendly feed contract
- [x] Contract tests for public feed
- [x] Minimal static reference frontend

### Runtime & Infrastructure
- [x] Cloud Run runtime managed via Terraform
- [x] Remote Terraform state in GCS with locking
- [x] Cloud Scheduler triggering `/internal/tick`
- [x] CI pipeline with tests, image build and deploy
- [x] Deterministic runtime initialization (fresh DB support)
- [x] Startup DB health check
- [x] Runtime-aware structured logging (JSON in container, text locally)

Status: **live**

---

## Post-MVP evolution

### A7 – Content quality & policy layer (v1) — DONE
- [x] Source-aware HTML cleaning layer
- [x] Spam marker removal (RemoteOK-specific artifacts)
- [x] Remote purity policy signals (soft tagging)
- [x] Geo restriction signals (soft tagging)
- [x] Global policy signal capture across all ingestion sources
- [x] Cleaning and policy test coverage
- [x] Audit scripts for source quality analysis (geo + remote purity)

### A8 – Observability & ops polish
- [x] Structured logging
- [x] Runtime metrics (tick duration, ingestion counts)
- [x] Tick summary metrics (per source: fetched / accepted / rejected)
- [x] Policy rejection metrics and reason tracking
- [x] Internal audit panel + filtered audit API (`/internal/audit`, `/internal/audit/jobs`)
- [ ] Rejection audit log (policy v1, persistent file-based)
- [ ] Scheduler and tick failure alerting

### A9 – Compliance resolution (v2) — DONE
- [x] Deterministic remote model classifier (`remote_only`, `non_remote`, etc.)
- [x] Deterministic geo classifier (`eu_member_state`, `non_eu`, etc.)
- [x] Compliance resolver (`approved` / `review` / `rejected`) with score `0..100`
- [x] Compliance resolution phase inside tick pipeline
- [x] Startup bootstrap for existing rows missing compliance fields
- [x] Feed quality threshold (`/jobs/feed` uses `min_compliance_score=80`)

### A10 – Database platform hardening
- [x] Connection backend split by runtime mode (`DB_MODE`)
- [x] Standard PostgreSQL mode via `DATABASE_URL`
- [x] CloudQL ready mode (`DB_MODE=cloudsql`, Cloud SQL connector + IAM auth)
- [ ] Explicit migration tooling (Alembic or equivalent)
- [ ] Index tuning aligned with lifecycle + feed query patterns
- [ ] Automated post-deploy smoke check wired into CI/CD

---

## Future (design-level)

- Company self-publishing workflow (manual, compliance-first)
- Metadata enrichment (source-provided fields such as posted_at; heuristic-based, no AI by default)
- Managed deployment options
- Compliance/policy evolution:
  - richer reason-code taxonomy persisted in DB
  - confidence-aware scoring calibration
  - drift detection per source (quality regression monitoring)
  - review workflow for borderline (`review`) offers
