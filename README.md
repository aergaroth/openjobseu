[![Tests](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml/badge.svg)](https://github.com/aergaroth/openjobseu/actions/workflows/tests.yml)

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
2. Ingestion runs for configured sources
3. Canonical rows are upserted into PostgreSQL
4. Compliance resolution computes `compliance_status` + `compliance_score`
5. Post-ingestion workers run availability checks and lifecycle transitions

### Active ingestion sources in the default registry
- `remotive` (public API)
- `employer_ing` (curated employers table + Greenhouse ATS API)

Adapters for `remoteok` and `weworkremotely` exist in codebase but are currently disabled in `app/workers/ingestion/registry.py`.

---

## API surface

Public/read-only:
- `GET /health`
- `GET /ready`
- `GET /jobs`
- `GET /jobs/feed`
- `GET /jobs/stats/compliance-7d`

Internal/ops:
- `POST /internal/tick`
- `GET /internal/audit`
- `GET /internal/audit/jobs`
- `GET /internal/audit/filters`
- `GET /internal/audit/stats/company`
- `GET /internal/audit/stats/source-7d`
- `POST /internal/audit/tick-dev`

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

Ingestion mode:
- `INGESTION_MODE=local` -> local JSON source (`ingestion/sources/example_jobs.json`)
- any other value (including `prod`, `dev`) -> pipeline mode with external handlers

Optional source selection in pipeline mode:
- `INGESTION_SOURCES=remotive,employer_ing`

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
