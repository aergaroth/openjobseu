# OpenJobsEU

[![CI Status](https://github.com/aergaroth/openjobseu/actions/workflows/prod_flow.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions)

OpenJobsEU is an open-source, compliance-first project focused on aggregating legally accessible, EU-wide remote job offers. 

The project is backend-first and infrastructure-oriented. It leverages a modern Serverless stack on Google Cloud to provide a zero-maintenance, zero-compute public feed, while the FastAPI runtime itself stays private behind Cloud Run IAM.

## Core Features

- **Compliance First**: Deterministic policy engine grading jobs by remote purity and EU geo-restrictions.
- **Zero-Compute Public Feed**: The public frontend is 100% static. Core layout is deployed at release, while the dynamic `feed.json` is exported iteratively by the backend to Google Cloud Storage and served via CDN. Dynamic runtime endpoints such as `/jobs`, `/companies`, and `/jobs/stats/compliance-7d` are not part of the public surface in production.
- **Modular Monolith**: Cleanly separated domains (Ingestion, Compliance, Operations) within a single Python FastAPI application.
- **Robust Async Processing**: Leverages Google Cloud Tasks and Cloud Scheduler for time-budgeted, idempotent, and heavily retried worker execution.
- **Strict Security**: Endpoints split between UI (Session-based via Google OAuth) and M2M routes (OIDC tokens with strict Audience validation). For local development (`APP_RUNTIME=local`), the system falls back to dummy placeholders to ensure low friction.
- **High Performance Data**: Scalable PostgreSQL database design with GIN Trigram indexing for fuzzy search and `GROUPING SETS` for real-time audit aggregations.

## Documentation

Detailed documentation detailing the design decisions and data flows is located in the `docs/` directory:

- System Architecture
- System Map
- Canonical Model
- Compliance & Data Usage
- Job Lifecycle
- Data Sources
- Roadmap

*Note: OpenJobsEU does not engage in scraping closed/protected platforms, nor does it automate applications.*