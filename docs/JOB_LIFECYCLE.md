# Job Lifecycle and Status Transitions

OpenJobsEU prioritizes job freshness and availability over raw volume.

## Status Definitions

- active
  The job offer is available and has been recently verified.

- stale 
  The job offer has not been verified within the expected time window.

- expired
  The job offer is no longer available (e.g. HTTP 404/410).

- unreachable
  The job source could not be reached during verification.

## State Transitions

new → active 
active → stale
stale → active
stale → expired
active → unreachable
unreachable → active
unreachable → expired

Expired jobs are not deleted immediately and may be retained for audit or analytics purposes.

## Verification Rules

- Newly ingested jobs are marked as active.
- Jobs are re-verified periodically based on source-specific TTL.
- A job is marked as stale if it exceeds its verification window.
- After multiple failed verification attempts, the job is marked as expired.
- Unreachable status is used when the source cannot be contacted, not when the job is gone.
