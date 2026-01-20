# Canonical Job Model – OpenJobsEU

The canonical job model defines a single, source-agnostic representation of job offers within OpenJobsEU.
All ingestion adapters must normalize incoming data to this model.

## Core Identifiers
- job_id: globally unique identifier (UUID)
- source: identifier of the original data source
- source_job_id: job identifier in the source system
- source_url: original job posting URL

## Job Metadata
- title: job title
- company_name: company or organization name
- company_website: optional company website
- description: normalized job description (plain text)
- employment_type: full-time | part-time | contract | freelance
- seniority: junior | mid | senior | lead | unspecified

## Location & Scope
- remote: boolean (must be true for inclusion)
- remote_scope: EU-wide | selected_countries
- country_restrictions: list of ISO country codes (if applicable)
- timezone_requirements: optional timezone constraints

## Skills & Tags
- tech_tags: list of normalized technology tags
- role_category: engineering | devops | data | security | other

## Compensation (Optional)
- salary_min: optional numeric
- salary_max: optional numeric
- salary_currency: ISO currency code
- salary_period: monthly | yearly | hourly

## Lifecycle & Tracking
- status: active | stale | expired | unreachable
- first_seen_at: timestamp
- last_seen_at: timestamp
- last_verified_at: timestamp
- verification_failures: integer

>first_seen_at and last_seen_at are initially set during ingestion.
>last_seen_at is expected to be updated on subsequent successful ingestions of the same job.
>last_verified_at represents the last successful availability verification performed by the validator component.


## Metadata
- created_at: timestamp
- updated_at: timestamp

## Ingestion Adapter Contract

Each ingestion adapter must:
- fetch job data from a single source
- map source fields to the canonical job model
- provide source identifier and source job ID
- set only the initial job status during ingestion

Adapters are not responsible for availability verification.
