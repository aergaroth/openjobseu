[![Tests](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml)

# OpenJobsEU

Project website: https://openjobseu.org (work in progress)

OpenJobsEU is an open-source, compliance-first platform for aggregating remote job offers across the European Union.

The project is built primarily as a DevOps and cloud-focused initiative, showcasing production-grade infrastructure, data ingestion pipelines, and observability patterns rather than a consumer job board.

## Live runtime (Cloud Run)

https://openjobseu-anobnjle6q-lz.a.run.app

## Goals
- Aggregate only legally accessible job data
- Focus exclusively on remote roles within the EU
- Verify job availability and data freshness
- Provide a transparent alternative to closed job platforms

## Non-Goals
- No scraping of commercial job boards
- No user profiling or advertising
- No automated posting to third-party platforms

## Core Features
- Source-specific ingestion adapters
- Canonical job data model
- Background availability verification
- Search and filtering API
- Infrastructure as Code (Terraform)
- CI/CD and observability

## Project Status
This is an early-stage open-source project developed as a portfolio and learning initiative.
Commercial use is not a current goal, but the architecture allows future extensions such as managed services or company publishing tools.

Implemented features:
- RSS ingestion (WeWorkRemotely as initial source)
- Persistent storage (SQLite)
- Job availability checking (HTTP-based)
- Lifecycle management (NEW -> ACTIVE -> STALE -> EXPIRED)
- Read-only Jobs API
- Automated scheduler (Cloud Run)

The system is designed as a tick-based worker, executed periodically.

## Documentation
- docs/ARCHITECTURE.md
- docs/DATA_SOURCES.md
- docs/COMPLIANCE.md
- docs/ROADMAP.md

### Hint:

>cp infra/gcp/terraform.tfvars.example infra/gcp/terraform.tfvars


## License
Apache License 2.0
