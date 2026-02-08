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

## MVP v1 — DONE

### A1 – Ingestion
- [x] Canonical job data model
- [x] Local JSON ingestion (dev)
- [x] RSS ingestion (WeWorkRemotely)
- [x] Public API ingestion (Remotive, RemoteOK)
- [x] Source-specific normalization with tests

### A2 – Persistence
- [x] SQLite storage
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

Status: **live**

---

## Next milestones

### A6.1 – Distribution polish (optional)
- CORS hardening for public feed consumers
- Optional reverse proxy under primary domain
- Frontend UX polish (sorting, client-side filtering)

### A7 – Observability & ops polish
- Structured logging
- Runtime metrics (tick duration, ingestion counts)
- Scheduler and tick failure alerting

### A8 – Storage upgrade
- Higher-level database engine backend
- Explicit schema and migrations
- Indexing aligned with read and lifecycle patterns

---

## Future (design-level)

- Company self-publishing workflow (manual, compliance-first)
- Metadata enrichment (heuristic-based, no AI by default)
- Managed deployment options
