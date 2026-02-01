# Data Sources – OpenJobsEU

OpenJobsEU integrates only **legally accessible job data sources**.

All sources are accessed in a read-only manner and processed through dedicated ingestion adapters that normalize data into the canonical job model.

---

## Current data sources

### RSS feeds

- **Type:** Public RSS feeds
- **Example:** WeWorkRemotely (remote programming jobs)
- **Purpose:** Primary production data source
- **Access:** Public, unauthenticated
- **Legal basis:** Publicly available job listings published by the source

RSS ingestion is the default production ingestion mode.

---

## Development-only sources

### Local JSON file

- **Type:** Local JSON file
- **Purpose:** Development and testing
- **Access:** No network access required
- **Legal basis:** Synthetic example data

Local ingestion is intended strictly for development and debugging and is never used in production.

---

## Planned sources

The following source types are considered for future stages:

- Additional public RSS or JSON feeds
- Company-provided job feeds or submissions
- Explicitly shared job datasets

Each new source will be evaluated individually for legal accessibility and compliance before integration.

---

## Source integration principles

Each data source is integrated through a dedicated adapter that is responsible for:
- fetching source data
- handling source-specific formats
- transforming data into the canonical job model

Adapters do not perform availability checks or lifecycle transitions.
