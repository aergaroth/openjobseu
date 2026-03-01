[![Tests](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml)

# OpenJobsEU

Project website: https://openjobseu.org
(Simple static frontend consuming the public job feed)

OpenJobsEU is an open-source, compliance-first platform for aggregating **EU-focused, fully remote job offers**.

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

The feed contains **EU-focused, fully remote roles** that pass compliance-score filtering and is intended for:
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
4. **Compliance resolution** computes `compliance_status` + `compliance_score`
5. Post-ingestion workers handle:
   - availability checks
   - lifecycle transitions

The system is designed so that **adding a new data source does not affect existing ones**.

---

## Goals
- Aggregate only **legally accessible** job data
- Focus on **EU-focused remote roles** (EU/EEA/UK signals)
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
- SQLAlchemy-based PostgreSQL storage backend (`DB_MODE=standard` / `DB_MODE=cloudsql`)
- Deterministic compliance classification and scoring (`approved` / `review` / `rejected`)
- Availability verification via HTTP checks
- Read-only Jobs API and public feed
- Internal audit API and HTML audit panel (`/internal/audit`)
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
- PostgreSQL persistence via SQLAlchemy engine abstraction
- Availability checking
- Lifecycle management (NEW → ACTIVE → STALE → EXPIRED)
- Compliance bootstrap for existing DB rows at startup
- Compliance resolution stage inside tick pipeline
- Public `/jobs` and `/jobs/feed` endpoints
- Feed filtering by compliance score threshold (`min_compliance_score=80`)
- Internal audit endpoints (`/internal/audit`, `/internal/audit/jobs`)
- Cloud Run + Cloud Scheduler runtime
- CI with validation and normalization tests

The system is intentionally conservative and correctness-oriented.

---

## Documentation
- `docs/ARCHITECTURE.md` – system design and ingestion flow
- `docs/DATA_SOURCES.md` – details of supported sources
- `docs/CANONICAL_MODEL.md` – canonical job schema
- `docs/COMPLIANCE.md` – data access and legal considerations
- `docs/JOB_LIFECYCLE.md` – lifecycle state transitions
- `docs/ROADMAP.md` – planned evolution

---

## Infrastructure hint

```bash
cp infra/gcp/terraform.tfvars.example infra/gcp/terraform.tfvars
```

---

## Runtime configuration (current)

Required database mode:

- `DB_MODE=standard` with `DATABASE_URL=postgresql+psycopg://...`
- or `DB_MODE=cloudsql` with `INSTANCE_CONNECTION_NAME`, `DB_NAME`, `DB_USER`

## Testing 📦

Most of the validator-level unit tests exercise real database logic, so they
expect a PostgreSQL server to be available. The GitHub Actions workflow starts
a `postgres:16` container and sets `DATABASE_URL` to
`postgresql+psycopg://postgres:postgres@localhost:5432/testdb`; you can
mimic that locally with your own container or an existing instance.

A simple pattern to run tests in development:

```bash
# start a throw‑away postgres
docker run --rm --name openjobspg -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=testdb -p 5432:5432 -d postgres:16

# run pytest; conftest.py will default DATABASE_URL to
# postgresql+psycopg://postgres:postgres@localhost:5432/testdb
pytest -q
```

If the database is unreachable, the test suite will skip the SQL-heavy
modules rather than failing outright, allowing you to edit code or run linters
without a running backend.

Ingestion runtime:

- `INGESTION_MODE=prod` (default pipeline with external sources)
- `INGESTION_MODE=local` (dev-only local JSON source)
- optional: `INGESTION_SOURCES=remotive,remoteok,weworkremotely`

---

## License

Apache License 2.0
