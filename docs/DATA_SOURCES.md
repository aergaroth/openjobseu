# Data Sources – OpenJobsEU

OpenJobsEU integrates only legally accessible, read-only sources.

Every record goes through:
- ATS adapter fetch
- adapter-level normalization
- compliance policy (`apply_policy`)
- canonical upsert
- post-ingestion lifecycle and availability

---

## Active Ingestion Path

### Employer ATS Ingestion (`employer_ing`)

- **Type:** Curated company list + ATS API fetch
- **Worker:** `app/workers/ingestion/employer.py`
- **Adapter registry:** `app/adapters/ats/registry.py`
- **Current ATS support:** Greenhouse, Lever, Workable, Ashby, Personio, Recruitee, SmartRecruiters, JobAdder, Teamtailor, Traffit, Breezy.

Input set is loaded from `companies` rows where:
- `is_active = true`
- `ats_provider IS NOT NULL`
- `ats_slug IS NOT NULL`

Current provider behavior:
- supported provider -> fetch + normalize + policy + persist
- unsupported/inactive provider -> skipped with ingestion metrics

`geo_restriction_hard` offers are flagged in metrics and persisted with a rejected status to enable broader market analytics.

---

## Source Integration Contract

Adapters:
- fetch ATS payloads
- normalize source records to canonical shape
- do not persist data directly

Ingestion worker:
- runs policy engine
- aggregates observability metrics
- writes canonical records to DB

Post-ingestion workers:
- run availability checks
- apply lifecycle transitions
- export static JSON feed to Cloud Storage

---

## Onboarding Criteria for New ATS Providers

A provider is enabled only after:
- legal accessibility/reuse confirmation
- stable payload quality
- deterministic normalization and policy behavior
- test coverage for adapter + ingestion integration

Scraping closed/protected platforms remains out of scope.

---

## Discovery Sources (ATS slug discovery)

Discovery uses multiple read-only sources for provider/slug candidates:
- careers-page crawler (`careers_crawler`)
- ATS guessing from company names (`ats_guessing`)
- reverse slug probing (`ats_reverse`)
- search-index dorking (`dorking`)
- certificate transparency logs (`dorking_crt`)
- shallow public URL harvesting (`slug_harvest`, `robots.txt` aware)

Candidate slugs are first stored in `discovered_slugs` and only promoted to `company_ats` after quality checks/probing.  
For Teamtailor, public discovery stores account candidates with `needs_token` status, because API access requires a per-company token not derivable from public URLs.

JobAdder uses a mixed contract:
- `company_ats.ats_slug` stores the public `board_id` extracted from careers URLs
- `JOBADDER_API_TOKEN` is a global environment secret used by the adapter for authenticated `fetch()` and `probe_jobs()`

## Discovery Diagnostics

When a provider seems missing from the final dataset, check the pipeline in this order:
- `discovered_slugs` — was a candidate provider/slug found at all?
- `company_ats` — was the candidate promoted to an active ATS integration?
- `job_sources` — did ingestion persist source mappings for this provider?
- `jobs` — did canonical jobs get created from those source mappings?

Example drill-down for one provider:

```sql
SELECT provider, slug, discovery_source, status, created_at
FROM discovered_slugs
WHERE provider = 'breezy'
ORDER BY created_at DESC
LIMIT 50;
```

```sql
SELECT provider, ats_slug, is_active, last_sync_at, updated_at
FROM company_ats
WHERE provider = 'breezy'
ORDER BY updated_at DESC
LIMIT 50;
```

```sql
SELECT source, source_job_id, last_seen_at
FROM job_sources
WHERE source LIKE 'breezy:%'
ORDER BY last_seen_at DESC
LIMIT 50;
```

```sql
SELECT DISTINCT j.job_id, j.title, js.source
FROM jobs j
JOIN job_sources js ON js.job_id = j.job_id
WHERE js.source LIKE 'breezy:%'
ORDER BY js.source, j.job_id
LIMIT 50;
```
