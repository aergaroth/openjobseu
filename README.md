# OpenJobsEU

[![CI Status](https://github.com/aergaroth/openjobseu/actions/workflows/prod_flow.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions)

OpenJobsEU is an open-source, compliance-first project focused on aggregating legally accessible, EU-wide remote job offers. 

The project is backend-first and infrastructure-oriented. It leverages a modern Serverless stack on Google Cloud to provide a zero-maintenance, zero-compute public feed, while the FastAPI runtime itself stays private behind Cloud Run IAM.

## Core Features

- **Compliance First**: Deterministic policy engine grading jobs by remote purity and EU geo-restrictions.
- **Zero-Compute Public Feed**: The public frontend is 100% static. `feed.json` is refreshed by the runtime maintenance pipeline, while `frontend/index.html`, `frontend/style.css`, and `frontend/feed.js` are published separately by CI after a successful production deploy. Both are served from Google Cloud Storage/CDN, and runtime endpoints such as `/jobs`, `/companies`, and `/jobs/stats/compliance-7d` are not part of the public surface in production.
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

## Public frontend publishing model

### 1. Runtime refresh: `feed.json`

- Trigger: regular maintenance/runtime pipeline ticks.
- Publisher: `app/workers/frontend_exporter.py` executed from the private backend pipeline.
- Artifact: only `feed.json`.
- Cadence: frequent, operational refreshes as jobs change.
- Cache policy: `Cache-Control: public, max-age=300`.

### 2. Deploy-time sync: static frontend assets

- Trigger: GitHub Actions `prod_flow.yml`, only after the production deploy job finishes successfully.
- Publisher: `scripts/publish_frontend_assets.py`, which reuses `run_frontend_export(..., sync_assets=True)` from `app/workers/frontend_exporter.py`.
- Artifacts: `frontend/index.html`, `frontend/style.css`, `frontend/feed.js`.
- Cadence: only on releases / explicit production deploys, not on each runtime tick.

### Asset ownership and cache busting

- `frontend/index.html` is published by CI/CD and remains the release-controlled entrypoint.
- `frontend/style.css` and `frontend/feed.js` are also published by CI/CD, not by the runtime worker.
- During publish, CI injects `?v=<release tag or commit SHA>` into the `index.html` references to `style.css` and `feed.js`, which provides simple cache busting for frontend changes without coupling asset deploys to `feed.json` refreshes.
- Runtime IAM can stay limited to `feed.json`, while asset publication can use a separate deploy credential.
