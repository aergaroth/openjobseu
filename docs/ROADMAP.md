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

### A6 – Distribution & consumption
- [x] Public JSON feed (`/jobs/feed`)
- [x] Stable, cache-friendly feed contract
- [x] Minimal static frontend consuming the feed
- [x] Contract tests for public feed

### Runtime & Infrastructure
- [x] Cloud Run runtime managed via Terraform
- [x] Remote Terraform state in GCS with locking
- [x] Cloud Scheduler triggering `/internal/tick`
- [x] CI pipeline with tests, image build and deploy
- [x] Deterministic runtime initialization (fresh DB support)

### A7 – Distribution & consumption
- [x] Public JSON feed (`/jobs/feed`)
- [x] Stable, versioned feed contract
- [x] Cache-friendly public endpoint
- [x] Contract tests for feed
- [x] Minimal reference frontend consuming the feed

Status: **live**

---

## Next milestones

### A7.1 – Distribution polish (optional)
- CORS hardening for public feed consumers
- Optional reverse proxy under primary domain
- Frontend UX polish (sorting, client-side filtering)

### A8 – Storage upgrade
- PostgreSQL backend
- Basic migrations

### A9 – Observability & ops polish
- Structured logging
- Basic runtime metrics
- Scheduler and tick failure alerting

---

## Future (design-level)

- Company self-publishing workflow (manual, compliance-first)
- Metadata enrichment (heuristic-based, no AI by default)
- Managed deployment options