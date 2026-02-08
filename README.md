[![Tests](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml)

# OpenJobsEU

Project website: https://openjobseu.org
(Simple static frontend consuming the public job feed)

OpenJobsEU is an open-source, compliance-first platform for aggregating **EU-wide, fully remote job offers**.

The project is built as a **backend-first, production-oriented system**, with a strong focus on:
- clean domain modeling
- ingestion correctness
- data lifecycle management
- real cloud deployment

It is **not** a consumer-facing job board.

---

## Live runtime (Cloud Run)

https://openjobseu-anobnjle6q-lz.a.run.app

---

## Public job feed

OpenJobsEU exposes a stable, read-only JSON feed of visible job offers:

https://openjobseu-anobnjle6q-lz.a.run.app/jobs/feed

The feed contains **EU-wide, fully remote roles only** and is intended for:
- minimal frontends
- external aggregators
- automated consumers

The contract is intentionally **minimal, cache-friendly, and read-only**.

---

## High-level architecture

At runtime, OpenJobsEU operates as a **tick-based ingestion system**:

1. **Cloud Scheduler** triggers `/internal/tick`
2. A **dispatcher** determines active ingestion sources
3. Each source runs through:
   - fetch-only adapter (external API / RSS)
   - source-specific normalization
   - idempotent persistence
4. Post-ingestion workers handle:
   - availability checks
   - lifecycle transitions

The system is designed so that **adding a new data source does not affect existing ones**.

---

## Goals
- Aggregate only **legally accessible** job data
- Focus exclusively on **EU-wide remote roles**
- Verify job availability and data freshness over time
- Provide a transparent, inspectable alternative to closed job platforms

---

## Explicit non-goals
- Scraping closed or protected job boards
- User accounts, profiles, or tracking
- Advertising, ranking, or recommendation systems
- Acting as a full-featured job board

---

## Core features
- Multiple ingestion sources with a unified dispatcher
- Fetch-only adapters and explicit normalization layer
- Canonical job data model
- Idempotent storage and lifecycle tracking
- Availability verification via HTTP checks
- Read-only Jobs API and public feed
- Structured ingestion logging
- Infrastructure as Code (Terraform)
- CI pipeline with automated tests

---

## Current status

OpenJobsEU is a **working early-stage system**, running in real cloud infrastructure.

### Implemented ingestion sources
- **WeWorkRemotely** (RSS)
- **Remotive** (public API)
- **RemoteOK** (public API)

### Implemented runtime components
- Tick dispatcher with pluggable sources
- Source-specific normalization
- SQLite persistence (dev / early prod)
- Availability checking
- Lifecycle management (NEW → ACTIVE → STALE → EXPIRED)
- Public `/jobs/feed` endpoint
- Cloud Run + Cloud Scheduler runtime
- CI with validation and normalization tests

The system is intentionally conservative and correctness-oriented.

---

## Documentation
- `docs/ARCHITECTURE.md` – system design and ingestion flow
- `docs/DATA_SOURCES.md` – details of supported sources
- `docs/CANONICAL_MODEL.md` – canonical job schema
- `docs/COMPLIANCE.md` – data access and legal considerations
- `docs/ROADMAP.md` – planned evolution

---

## Infrastructure hint

```bash
cp infra/gcp/terraform.tfvars.example infra/gcp/terraform.tfvars
```

---

## License

Apache License 2.0

