# Job Lifecycle and Status Transitions

OpenJobsEU prioritizes **job freshness and availability** over raw job volume.

Each job progresses through a well-defined lifecycle driven by periodic verification and ingestion events.

---

## Status definitions

Jobs move through the following lifecycle states:

- **NEW**
  Freshly discovered job, within the first 24 hours after `first_seen_at`.

- **ACTIVE** 
  Verified and visible job.

- **STALE**
  Job that has not been successfully verified within its expected verification window.

- **UNREACHABLE**
  Job whose source could not be reached during availability verification (temporary state).

- **EXPIRED** 
  Job confirmed unavailable or outdated after repeated failed verifications.

From an API consumer perspective, **NEW and ACTIVE jobs are treated as visible**.

---

## State transitions

The lifecycle supports the following transitions:

new → active
active → stale 
stale → active 
stale → expired
active → unreachable
unreachable → active
unreachable → expired

Expired jobs are not deleted immediately and may be retained for audit or analytical purposes.

---

## Verification and transition rules

- Newly ingested jobs are initially marked as **NEW**.
- Jobs are periodically re-verified based on source-specific TTL rules.
- If a job exceeds its verification window, it transitions to **STALE**.
- A successful verification returns a **STALE** or **UNREACHABLE** job to **ACTIVE**.
- Temporary connectivity issues result in **UNREACHABLE** status.
- After multiple consecutive verification failures, a job transitions to **EXPIRED**.

Lifecycle transitions are handled asynchronously by the availability worker and do not block ingestion or API access.

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
