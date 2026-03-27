# OpenJobsEU

[![CI Status](https://github.com/aergaroth/openjobseu/actions/workflows/ci.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/ci.yml)

OpenJobsEU is an open-source, compliance-first project focused on aggregating legally accessible, EU-wide remote job offers. 

The project is backend-first and infrastructure-oriented. It leverages a modern Serverless stack on Google Cloud to provide a zero-maintenance, zero-compute public feed, while the FastAPI runtime itself stays private behind Cloud Run IAM.

## Core Features

- **Compliance First**: Deterministic policy engine grading jobs by remote purity and EU geo-restrictions.
- **Zero-Compute Public Feed**: The public frontend is 100% static. `feed.json` is refreshed by the runtime maintenance pipeline, while `frontend/index.html`, `frontend/style.css`, and `frontend/feed.js` are published separately by CI after a successful production deploy. Both are served from Google Cloud Storage/CDN, and runtime endpoints such as `/jobs`, `/companies`, and `/jobs/stats/compliance-7d` remain private Cloud Run interfaces in production rather than public internet APIs.
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

## Merge gatekeepers vs deploy workflows

- **Merge gatekeeper:** `ci.yml` runs the full `pytest` suite for pull requests targeting `main` and `develop`. This is the required status check that should block merges until green.
- **Additional PR quality checks:** `pre-commit.yml` continues to validate pre-commit hooks and Commitizen commit-message compliance on pull requests.
- **Infra PRs:** `terraform-plan.yml` runs `terraform validate` and `terraform plan` on pull requests that touch `infra/**`.
- **Deploy only:** `dev_flow.yml` deploys after pushes to `develop` (typically after merge), and `prod_flow.yml` handles release/deploy steps after pushes to `main`. Neither workflow runs on pull requests.
- **No duplicated full flow:** feature-branch pushes do not trigger the deploy workflows, while PRs trigger only `ci.yml`/`pre-commit.yml`. The deploy workflows run only after the merge commit lands on `develop` or `main`.
- **Branch-maintenance automation:** `sync_main_to_develop.yml` keeps `develop` aligned with release changes merged to `main`, and `protect_develop.yml` recreates `develop` if the branch is deleted.
- **Branch protection:** configure GitHub branch protection for both `main` and `develop` so the required status check includes `CI / pytest` before merge.

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

## GitHub Actions → GCP Workload Identity Federation

The repository now assumes **OIDC-based federation** between GitHub Actions and Google Cloud instead of long-lived JSON keys.

### Trust model after migration

- GitHub Actions requests a short-lived OIDC token from `token.actions.githubusercontent.com`.
- GCP Workload Identity Federation verifies the token against a dedicated provider in each project (`dev-openjobseu` and `openjobseu`).
- The provider trusts only this repository: `aergaroth/openjobseu`.
- `dev` trust accepts only:
  - `push` / `workflow_dispatch` runs from `refs/heads/develop`
  - `pull_request` runs whose `base_ref` is `develop`
- `prod` trust accepts only:
  - `push` / `workflow_dispatch` runs from `refs/heads/main`
  - `pull_request` runs whose `base_ref` is `main`
- Each workflow step then impersonates a dedicated Google service account with the minimum role set for its purpose.

### Service accounts and least-privilege split

- `github-deploy` (dev/prod): builds and pushes the container image, runs `terraform apply`, and therefore needs Artifact Registry write access, Terraform state bucket object access, Cloud Run/Scheduler/Tasks admin, Secret Manager admin, project IAM admin, plus `iam.serviceAccountUser` on the runtime and scheduler identities.
- `github-terraform-plan` (dev/prod): used only by PR plans; it gets read-only access to the Terraform state bucket and project metadata (`roles/viewer` + `roles/secretmanager.viewer`).
- `github-assets-publish` (prod): used only after a successful production deploy to publish `frontend/index.html`, `frontend/style.css`, and `frontend/feed.js`; it only receives `roles/storage.objectAdmin` on the public bucket.
- The Cloud Run runtime account remains separate and still owns only runtime responsibilities (for example the conditional write access to `feed.json`).

### GitHub configuration after `terraform apply`

Create/update GitHub **repository variables** (not secrets) with the Terraform outputs from each environment:

- `GCP_WIF_PROVIDER_DEV`
- `GCP_SERVICE_ACCOUNT_DEV`
- `GCP_SERVICE_ACCOUNT_TERRAFORM_PLAN_DEV`
- `GCP_WIF_PROVIDER_PROD`
- `GCP_SERVICE_ACCOUNT_PROD`
- `GCP_SERVICE_ACCOUNT_TERRAFORM_PLAN_PROD`
- `GCP_SERVICE_ACCOUNT_ASSETS_PROD`

The remaining application secrets (`DEV_GOOGLE_CLIENT_SECRET`, `PROD_GOOGLE_API_KEY`, etc.) stay in GitHub Secrets because they are application data, not cloud authentication material.

### Migration / cleanup checklist

1. Run `terraform apply` in `infra/gcp/dev` and `infra/gcp/prod` to create the workload identity pools/providers, service accounts, and IAM bindings.
2. Copy the Terraform outputs into the GitHub repository variables listed above.
3. Trigger `terraform-plan.yml`, `dev_flow.yml`, and `prod_flow.yml` once to confirm OIDC authentication works end to end.
4. After successful verification, delete the legacy GitHub Secrets `GCP_SA_KEY_DEV` and `GCP_SA_KEY_PROD`.

## Testing

Most tests expect PostgreSQL. CI starts `postgres:16` and uses:
- `DB_MODE=standard`
- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/testdb`

*Note: The test suite explicitly blocks external HTTP requests to prevent accidental hangs or timeouts. Fast `DELETE` sweeps are used over `TRUNCATE CASCADE` for near-instant teardowns.*

Local pattern:

```bash
# start postgres
docker run --rm --name openjobspg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=testdb -p 5432:5432 -d postgres:16
