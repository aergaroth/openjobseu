# Data Sources – OpenJobsEU

OpenJobsEU integrates **only legally accessible, public job data sources**.

All sources are accessed in a **read-only** manner and processed through dedicated
ingestion adapters. Raw data is never exposed directly — every job offer must pass
through explicit normalization and validation before being persisted.
Final compliance status is assigned in a dedicated compliance-resolution stage.

---

## Current data sources

### WeWorkRemotely

- **Type:** Public RSS feed
- **Endpoint:** 
  https://weworkremotely.com/categories/remote-programming-jobs.rss
- **Access:** Public, unauthenticated
- **Legal basis:** Publicly published job listings
- **Scope:** Fully remote roles (EU-wide by project policy)

Notes:
- RSS entries are fetched as-is
- Normalization applies a conservative company-name heuristic
- Normalization uses source publication date when available (`published` / `updated`)
- Source URL is sanitized before persistence
- Jobs without required fields are skipped

---

### Remotive

- **Type:** Public JSON API
- **Endpoint:**
  https://remotive.com/api/remote-jobs
- **Access:** Public, unauthenticated
- **Legal basis:** Public API explicitly intended for reuse
- **Scope:** EU-wide and Worldwide roles only

Notes:
- Raw API payloads are fetched without modification
- Normalization enforces source-level scope constraints:
  - EU-wide or Worldwide only
  - non-Europe / non-worldwide location labels are skipped
- `publication_date` is used as `first_seen_at` when available
- URL and location fields are sanitized during normalization

---

### RemoteOK

- **Type:** Public JSON API
- **Endpoint:**
  https://remoteok.com/api
- **Access:** Public, unauthenticated
- **Legal basis:** Public API with explicit reuse allowance
- **Scope:** Remote-first roles, normalized into `EU-wide` or `worldwide`

Notes:
- The first API element (metadata/legal notice) is ignored
- Remaining entries are treated as job offers
- Normalization validates required fields and remote metadata
- Source date (`date` / `epoch`) is used for `first_seen_at` when available
- Source URL is sanitized before persistence

---

## Development-only sources

### Local JSON file

- **Type:** Local JSON file
- **Purpose:** Development and testing only
- **Access:** No network access required
- **Legal basis:** Synthetic example data

Local ingestion is used exclusively when:

```bash
INGESTION_MODE=local
```
It is never enabled in production deployments.

---

### Source integration principles

Each data source follows the same strict integration model:

### Adapters (fetch-only)

Adapters are responsible only for:

- fetching raw source data
- handling source-specific formats
- returning unmodified payloads

Adapters must not:

- apply heuristics
- perform normalization
- persist data
- modify lifecycle state

---

## Normalization

Normalization is handled separately and is responsible for:

- validating required fields
- enforcing source-specific structural and scope constraints
- mapping raw payloads to the canonical job model
- preparing records for downstream compliance scoring

Compliance resolution (separate worker stage) is responsible for:
- deriving `remote_class` and `geo_class`
- computing `compliance_status` and `compliance_score`
- enabling feed-quality filtering (`/jobs/feed` uses score threshold)

Normalization logic is:
- source-specific
- deterministic
- covered by automated tests

---

## Planned sources

Future sources may include:

- additional public RSS feeds
- public job APIs
- company-provided feeds or submissions

Each new source will be evaluated individually for:

- legal accessibility
- reuse permissions
- data stability
- alignment with OpenJobsEU scope

No scraping of closed or protected platforms is planned or permitted.
