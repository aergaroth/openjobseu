# OpenJobsEU Roadmap

## MVP v1
- Single canonical job data model
- Ingestion from legally accessible sources
- Background availability verification
- Search and filtering API
- Infrastructure as Code
- CI/CD pipeline
- Observability and health checks

## v2 (Design Only)
- Company self-publishing workflow
- Job publishing orchestration (no automated posting)
- AI-assisted metadata enrichment
- Managed deployment options

## Explicit Non-Goals
- Scraping closed job boards
- Automated posting to third-party platforms
- Candidate accounts or profiling

## Current state
- Architecture and core domain model defined
- Ingestion and validation pipeline implemented
- CI pipeline with tests enabled

## Project direction

OpenJobsEU is developed incrementally, starting from a strong infrastructure and domain foundation.
The long-term goal is a fully deployed, production-grade platform running in real cloud infrastructure,
rather than a purely demonstrational or mock project.


## Milestone: Runtime heartbeat (Cloud Scheduler)

- Cloud Run runtime managed via Terraform
- Remote Terraform state in GCS with locking
- Cloud Scheduler triggers `/internal/tick`
- CI enforces `terraform plan` on PRs

Status: live
