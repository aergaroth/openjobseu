# Compliance and Data Usage

OpenJobsEU is designed with **compliance, transparency, and legal clarity** as first-class concerns.

The platform intentionally limits its scope to avoid legal ambiguity and unethical data usage patterns common in commercial job aggregation.

---

## Data sources

OpenJobsEU processes job data exclusively from sources that are:

- publicly accessible without authentication
- explicitly intended for public distribution

Current and planned source types include:
- public APIs
- open job feeds (JSON / RSS)
- explicitly shared company submissions

Each source is evaluated individually before integration.

---

## Runtime compliance model (implemented)

OpenJobsEU uses deterministic, code-defined compliance stages:

1. Ingestion + normalization produce canonical job records
2. Policy signals/classifiers derive remote and geo classes
3. Compliance resolver assigns:
   - `compliance_status`: `approved | review | rejected`
   - `compliance_score`: `0..100`

Public distribution uses this score conservatively:
- `/jobs/feed` exposes only visible jobs with `compliance_score >= 80`

This approach keeps ingestion broad enough for auditability while keeping the public feed conservative.

---

## Explicit non-actions

OpenJobsEU does **not** engage in any of the following:

- scraping closed, protected, or commercial job platforms
- bypassing technical or legal access restrictions
- automating interactions with third-party systems
- storing or redistributing proprietary or copyrighted content

It also does not perform AI-generated policy decisions for inclusion.
Compliance logic is deterministic and test-covered.

---

## Legal boundaries

OpenJobsEU does not automate job posting to external platforms and does not act on behalf of companies or candidates.

Any future publishing-related functionality, if introduced, will be limited to:
- assisted workflows
- explicit, manual user actions
- clearly defined legal boundaries

The project prioritizes long-term legal sustainability over short-term data volume.
