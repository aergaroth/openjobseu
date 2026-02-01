# System Architecture – OpenJobsEU

## Overview
OpenJobsEU is an open-source, compliance-first platform designed to aggregate legally accessible remote job offers across the European Union.

The system is built with a strong emphasis on:
- clear separation of concerns
- data freshness and availability
- infrastructure automation
- operational transparency

It intentionally prioritizes infrastructure and platform design over user-facing features.

---

## High-Level Architecture

![Architecture diagram](./architecture.png)

>>Availability Checker runs asynchronously as a background worker 
>>and does not block ingestion or API requests.

---

## Core Components

### Ingestion Adapters
Each external job source is integrated through a dedicated ingestion adapter responsible for:
- fetching job data
- handling rate limits
- retrying failed requests
- transforming source-specific data into the canonical job model

Adapters are isolated to ensure failures in one source do not affect the rest of the system.

### Ingestion mode

OpenJobsEU supports two ingestion modes:

- `rss` (default) – real job ingestion via RSS feeds
- `local` – development-only ingestion from local JSON file

The mode is controlled via the `INGESTION_MODE` environment variable.

Example (development fallback):
```INGESTION_MODE=local```

Local ingestion is intended for debugging and testing only and is not used in production.

The system operates as a periodic worker:
ingestion → persistence → availability → lifecycle → read API.


---

### Normalization Layer
All incoming job data is normalized into a single canonical model to ensure:
- consistent querying
- predictable filtering
- source-agnostic processing

The normalization layer enforces mandatory fields and rejects invalid or incomplete entries.

---

### Job Store
The job store acts as the system’s single source of truth and is responsible for:
- persisting normalized job data
- tracking job status and lifecycle
- storing timestamps related to availability checks

---

### Availability Checker
Job availability is verified asynchronously by a background worker that:
- periodically checks original job URLs
- interprets HTTP status codes
- marks jobs as active, stale, expired, or unreachable

This component ensures the platform prioritizes data freshness over raw volume.

---

### Search API
The Search API exposes job data for consumers and supports:
- keyword search
- filtering by job attributes
- filtering by availability status
- sorting by freshness

The API is designed to be stateless and horizontally scalable.

### API (v1)

#### List jobs

GET /jobs

Query parameters:
- status: visible | new | active | stale | expired
- limit: default 20
- offset: default 0

Example:
GET /jobs?status=visible

---

### Frontend
The frontend provides a minimal interface for:
- browsing job offers
- applying filters
- redirecting users to original job postings

It intentionally avoids advanced personalization or tracking.

---

## Infrastructure

OpenJobsEU infrastructure follows modern cloud-native practices:
- containerized services
- Infrastructure as Code (Terraform)
- automated CI/CD pipelines
- environment-based configuration

The system is designed to run on a single cloud provider initially, with portability in mind.

---

## Observability

Operational visibility is treated as a first-class concern:
- health check endpoints
- metrics for ingestion success and failure
- metrics for job freshness and availability

Alerts are configured to detect:
- ingestion failures
- stale job data
- unavailable sources

---

## Compliance and Legal Boundaries

OpenJobsEU explicitly avoids:
- scraping closed or commercial job platforms
- automating interactions with third-party systems
- storing or redistributing proprietary content

All data processing is limited to legally accessible sources or explicit submissions.
