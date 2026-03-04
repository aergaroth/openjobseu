# Data Sources – OpenJobsEU

OpenJobsEU integrates only legally accessible, read-only sources.

Every record goes through:
- fetch adapter
- source normalization
- policy/classification signals
- canonical upsert
- compliance resolution

---

## Active in Default Ingestion Registry

### Remotive

- **Type:** Public JSON API
- **Endpoint:** `https://remotive.com/api/remote-jobs`
- **Handler key:** `remotive`
- **Normalization:** `app/workers/normalization/remotive.py`
- **Policy stage:** `policy v1` soft signals

Normalization rules include:
- required field validation
- location filter: Europe or Worldwide only
- publication date fallback to ingestion timestamp
- URL/location sanitization

---

### Employer ATS Ingestion (`employer_ing`)

- **Type:** Curated company list + ATS API fetch
- **Handler key:** `employer_ing`
- **Current ATS support:** Greenhouse only
- **Adapter:** `ingestion/adapters/greenhouse_api.py`
- **Normalization:** `app/workers/normalization/greenhouse.py`
- **Policy stage:** `policy v3`

Input set is loaded from `companies` table rows where:
- `is_active = true`
- `ats_provider IS NOT NULL`
- `ats_slug IS NOT NULL`

Current provider behavior:
- `ats_provider=greenhouse` -> fetch and ingest supported
- other providers -> skipped as unsupported

Policy v3 may hard-reject geo-restricted offers (`geo_restriction_hard`) before persistence.

---

## Present in Code, Disabled by Default

These adapters/workers exist but are commented out in `app/workers/ingestion/registry.py`:

- `remoteok` (`https://remoteok.com/api`)
- `weworkremotely` (RSS feeds)

If `INGESTION_SOURCES` references a source not present in registry handlers, pipeline metrics mark it as `unknown`.

---

## Development-Only Source

### Local JSON

- **Path:** `ingestion/sources/example_jobs.json`
- **Mode:** `INGESTION_MODE=local`
- **Usage:** local development/testing only

In local mode the runtime uses `run_tick()` (local loader path) instead of pipeline handlers.

---

## Source Integration Contract

Adapters:
- fetch source payloads
- handle network/transport concerns
- do not persist data

Normalization:
- validates source records
- maps to canonical fields
- rejects malformed/out-of-scope records

Downstream workers:
- derive classes and compliance outcome
- execute availability and lifecycle maintenance

---

## Onboarding Criteria for New Sources

A source is enabled in default registry only after:
- legal accessibility/reuse confirmation
- stable payload quality
- deterministic normalization and policy behavior
- test coverage for normalization and pipeline integration

Scraping closed/protected platforms remains out of scope.
