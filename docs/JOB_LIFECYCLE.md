# Job Lifecycle and Status Transitions

OpenJobsEU prioritizes job freshness and availability over raw volume.

## Status Definitions

Jobs move through the following lifecycle states:

- **NEW** – freshly discovered job (first 24h after first_seen_at)
- **ACTIVE** – confirmed, visible job
- **STALE** – not verified for more than 7 days
- **EXPIRED** – unreachable or outdated job
- **UNREACHABLE** - the job source could not be reached during verification.

>A job marked as ```stale``` is not re-verified until explicitly scheduled.

From a user perspective, **NEW and ACTIVE jobs are treated as visible**.

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
