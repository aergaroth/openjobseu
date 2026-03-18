[![Prod Flow](https://github.com/aergaroth/openjobseu/actions/workflows/prod_flow.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/prod_flow.yml)

# OpenJobsEU

Project website: https://openjobseu.org  
(Simple static frontend consuming the public job feed)

OpenJobsEU is an open-source, compliance-first platform for aggregating EU-focused remote job offers.

The project is backend-first and production-oriented, with focus on:
- ingestion correctness
- deterministic policy/compliance classification
- lifecycle freshness and availability checks
- cloud runtime operability

It is not a full consumer job board.

---

## Current runtime snapshot

OpenJobsEU runs as a tick-based pipeline:

1. Scheduler or operator triggers `POST /internal/tick`
2. Employer ATS ingestion runs (`employer_ing`)
3. Adapters normalize data, policy is applied, and taxonomy is classified
4. Canonical rows are upserted into PostgreSQL
5. Post-ingestion workers run lifecycle transitions, availability checks, and market metrics computation

### Active ingestion source
- `employer_ing` (curated employers table + ATS APIs)
- ATS Adapters are located in `app/adapters/ats/`

---

## API surface

Public/read-only:
- `GET /health`
- `GET /ready`
- `GET /jobs`
- `GET /jobs/feed`
- `GET /jobs/stats/compliance-7d`

Internal/ops:
*Auth:* `/login`, `/auth`, `/logout`
*Pipelines:* 
- `POST /internal/tick?incremental=true|false&limit=100` (Main ingestion)
- `POST /internal/discovery/run` (ATS discovery)
*Audit UI:* 
- `GET /internal/audit` (Protected by Google OAuth)
- `GET /internal/metrics`
- `GET /internal/audit/jobs`, `/filters`, `/stats/company`, `/stats/source-7d`
- `GET /internal/audit/ats-health`
*Actions/Ops:*
- `POST /internal/audit/tick-dev`
- `POST /internal/audit/ats-force-sync/{id}`
- `POST /internal/audit/ats-deactivate/{id}`
- `POST /internal/backfill-compliance`
- `POST /internal/backfill-salary`
- `POST /internal/backfill-department`
*Discovery granular:* `/internal/discovery/careers`, `/internal/discovery/guess`, `/internal/discovery/ats-reverse`, `/internal/discovery/company-sources`
*Async Tasks:* `POST /internal/tasks/{task_name}`, `GET /internal/tasks/{task_id}` (For long-running backfills and pipelines bypassing Cloud Run limits)

Feed contract:
- `/jobs/feed` returns only visible jobs (`new`, `active`)
- feed applies `min_compliance_score=80`
- feed response has `Cache-Control: public, max-age=300`

Stats contracts:
- `/jobs/stats/compliance-7d` returns global 7-day compliance aggregate by `first_seen_at`
- `/internal/audit/stats/company` returns company-level compliance ratio (default threshold: total jobs > 10)
- `/internal/audit/stats/source-7d` returns source-level compliance ratio for last 7 days

Audit panel behavior:
- filter dropdowns are registry-driven and include dynamic `source` values from DB
- panel includes two additional stats tables (company compliance ratio and source compliance ratio 7d)

---

## Runtime configuration

Database backend:
- `DB_MODE=standard` with `DATABASE_URL=postgresql+psycopg://...`
- or `DB_MODE=cloudsql` with `INSTANCE_CONNECTION_NAME`, `DB_NAME`, `DB_USER`

Ingestion orchestration:
- `run_pipeline()` is the main tick orchestrator
- Pipeline executes `run_employer_ingestion()`, `run_lifecycle_pipeline()`, `run_availability_pipeline()`, and `run_market_metrics_worker()`

Authentication (Audit Panel):
- Google OAuth protects `/internal/audit` and its API calls. Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SESSION_SECRET_KEY`.
- Automated GCP services (Cloud Scheduler/Cloud Run) bypass OAuth via `X-Goog-Authenticated-User-Email` headers or local dev exceptions.

Log rendering:
- `APP_RUNTIME=local` forces text logs/tick text output in `format=auto`
- container/cloud runtime defaults to JSON logs

### Internal tick formatting

`POST /internal/tick?format=auto|text|json`:
- `auto`: text on local runtime, JSON in container/cloud runtime
- `text`: always tabular plain-text summary
- `json`: always JSON payload

Examples:

```bash
curl -X POST "http://127.0.0.1:8000/internal/tick?format=text"
curl -X POST "http://127.0.0.1:8000/internal/tick?format=json"
```

---

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

# run tests
pytest -q
```

---

## Infrastructure hint

Terraform environments are split:

```bash
cp infra/gcp/dev/terraform.tfvars.example infra/gcp/dev/terraform.tfvars
cp infra/gcp/prod/terraform.tfvars.example infra/gcp/prod/terraform.tfvars
```

---

## Documentation

- `docs/ARCHITECTURE.md` - system design and ingestion flow
- `docs/DATA_SOURCES.md` - source inventory and activation status
- `docs/CANONICAL_MODEL.md` - canonical job schema
- `docs/COMPLIANCE.md` - data access and legal boundaries
- `docs/JOB_LIFECYCLE.md` - lifecycle status transitions
- `docs/ROADMAP.md` - current roadmap

---

## License

Apache License 2.0
