[![Tests](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml)

# OpenJobsEU

Project website: https://openjobseu.org (work in progress)

OpenJobsEU is an open-source, compliance-first platform for aggregating remote job offers across the European Union.

The project is built as a **production-oriented backend system**, with a strong focus on DevOps, cloud infrastructure, and data lifecycle management — not as a consumer-facing job board.

---

## Live runtime (Cloud Run)

https://openjobseu-anobnjle6q-lz.a.run.app

---

## Goals
- Aggregate only legally accessible job data
- Focus exclusively on remote roles within the EU
- Verify job availability and data freshness over time
- Provide a transparent alternative to closed job platforms

---

## Non-Goals
- Scraping of commercial or closed job boards
- User profiling, tracking, or advertising
- Automated posting to third-party platforms

---

## Core features
- Source-specific ingestion adapters (RSS, extensible)
- Canonical job data model
- Persistent storage and idempotent upserts
- Background availability verification
- Job lifecycle management (NEW -> ACTIVE -> STALE -> EXPIRED)
- Read-only Jobs API with filtering
- Infrastructure as Code (Terraform)
- CI/CD pipelines and basic observability

---

## Current status

OpenJobsEU is a working, early-stage system running in real cloud infrastructure.

Implemented features:
- RSS ingestion (WeWorkRemotely as initial source)
- Persistent storage (SQLite)
- HTTP-based job availability checks
- Time- and failure-based lifecycle management
- Read-only Jobs API
- Automated scheduler (Cloud Run)

The system operates as a **tick-based worker**, executed periodically via Cloud Scheduler.

---

## Documentation
- docs/ARCHITECTURE.md
- docs/DATA_SOURCES.md
- docs/COMPLIANCE.md
- docs/ROADMAP.md

---

## Infrastructure hint

```bash
cp infra/gcp/terraform.tfvars.example infra/gcp/terraform.tfvars
```

---

## License

Apache License 2.0

