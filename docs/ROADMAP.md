# OpenJobsEU Roadmap

## Project scope

OpenJobsEU is an open-source, compliance-first platform for aggregating remote job offers within the EU.

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

## MVP v1 — DONE ✅

### A1 – Ingestion
- [x] Canonical job data model
- [x] Local JSON ingestion (dev)
- [x] RSS ingestion (WeWorkRemotely)

### A2 – Persistence
- [x] SQLite storage
- [x] Idempotent job upsert
- [x] First-seen and last-seen tracking

### A3 – Availability checking
- [x] HTTP-based availability checks
- [x] Failure tracking and retries

### A4 – Lifecycle management
- [x] NEW / ACTIVE / STALE / EXPIRED states
- [x] Time-based transitions
- [x] Failure-based expiration

### A5 – Read API
- [x] GET /jobs endpoint
- [x] Status filtering
- [x] Visible jobs abstraction (new + active)

### Runtime & Infrastructure
- [x] Cloud Run runtime managed via Terraform
- [x] Remote Terraform state in GCS with locking
- [x] Cloud Scheduler triggering `/internal/tick`
- [x] CI pipeline with tests, image build and deploy

Status: **live**

---

## Next milestones

### A6 – Advanced filtering
- Technology tags
- Role / category filtering
- Company filtering

### A7 – Distribution
- Minimal frontend or JSON feed
- Public API documentation

### A8 – Storage upgrade
- PostgreSQL backend
- Basic migrations

---

## Future (design-level)

- Company self-publishing workflow
- AI-assisted metadata enrichment
- Managed deployment options
