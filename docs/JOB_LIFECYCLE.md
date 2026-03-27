# Job Lifecycle and Status Transitions

OpenJobsEU prioritizes **job freshness and availability** over raw job volume.

Each job progresses through a well-defined lifecycle driven by periodic verification and ingestion events. The system uses two distinct status fields to manage this: `availability_status` and `status`.

---

## Status Fields Explained

### `availability_status` (The Observation)

This field is written by the **Availability Worker** and represents the direct result of checking a job's URL. It is a raw observation.

- **active**: The URL returned a success code (2xx).
- **expired**: The URL returned a "not found" code (404, 410).
- **unreachable**: The URL could not be reached (timeout, DNS error, 5xx server error).

### `status` (The Lifecycle State)

This field is written exclusively by the **Lifecycle Worker**. It represents the canonical state of the job and determines its visibility in the API. The lifecycle worker uses `availability_status`, timestamps, and failure counts to make its decision.

- **NEW**
  Freshly discovered job, within the first 24 hours after `first_seen_at`.

- **ACTIVE**
  Verified and visible job.

- **STALE**
  Job that has not been successfully verified recently.

- **EXPIRED**
  Job confirmed unavailable or outdated.

From an API perspective:
- `/jobs` with `status=visible` maps to **NEW + ACTIVE**
- the application-level feed view applies visible-job filtering plus the compliance threshold
- the public dataset contract is the static `feed.json` export served from GCS/CDN

---

## State Transitions (`status` field)

The lifecycle worker orchestrates the following transitions for the main `status` field:

new → active
active → stale
stale → active
(active, stale) → expired

Expired jobs are not deleted immediately and may be retained for audit or analytical purposes.

---

## Verification and transition rules

The process is a two-step pipeline:

1.  **Availability Check**: The `availability` worker periodically fetches jobs and checks their `source_url`. It records the outcome in the `availability_status` column without changing the main `status`. *(Runs using adaptive time-budgeting to maximize throughput without hitting serverless timeouts).*

2.  **Lifecycle Transition**: The `lifecycle` worker runs as a separate process. It applies a set of rules in SQL to update the main `status` for all jobs in the database based on their current state, timestamps, and `availability_status`.

Key rules implemented by the lifecycle worker:
- A **NEW** job becomes **ACTIVE** after 24 hours.
- An **ACTIVE** job becomes **STALE** if it hasn't been successfully verified for over 7 days.
- A **STALE** job becomes **ACTIVE** again if it has been recently and successfully verified (i.e., `availability_status` is `active`).
- Any job becomes **EXPIRED** if:
    - Its `availability_status` is `expired`.
    - It has not been verified for over 30 days.
    - It has accumulated 3 or more consecutive `verification_failures`.

This separation ensures that the lifecycle state is managed centrally and consistently, based on the latest available data from verification checks.

---

## Lifecycle vs compliance

Lifecycle freshness and compliance quality are independent dimensions:
- lifecycle controls recency/availability (`new`, `active`, `stale`, `expired`, `unreachable`)
- compliance controls policy confidence (`approved`, `review`, `rejected`) with numeric score

Public feed distribution combines both dimensions conservatively.

---

## Source posting date (informational)

Some data sources provide an original publication date for job offers (`posted_at`).

Notes:
- `posted_at` is **not** used directly to drive lifecycle transitions
- lifecycle state is determined by `first_seen_at` and verification results
- `posted_at` may be used in the future to:
  - improve ingestion filtering
  - avoid re-ingesting very old offers
  - support audit and analytical use cases

This separation ensures consistent behavior across sources with varying data quality.

---

## Scheduling model

Lifecycle updates are executed as part of a periodic **tick-based worker**, triggered by the scheduler.

This design ensures:
- predictable system behavior
- separation of ingestion and verification concerns
- resilience to transient source failures
