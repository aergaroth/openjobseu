# Looker Studio Audit Dashboard

## Summary

OpenJobsEU uses a private, read-only Looker Studio dashboard backed directly by
Aiven PostgreSQL.

The report contract is exposed through dedicated SQL views in `public`:
- `vw_looker_audit_overview`
- `vw_looker_audit_company_stats`
- `vw_looker_audit_source_7d`
- `vw_looker_audit_source_trend`
- `vw_looker_audit_rejection_reasons`
- `vw_looker_audit_ats_health`
- `vw_looker_audit_companies`
- `vw_looker_audit_jobs`

The drill-down views are intentionally capped:
- `vw_looker_audit_companies` -> `LIMIT 10000`
- `vw_looker_audit_jobs` -> `LIMIT 25000`

This is deliberate. Free Looker Studio can silently truncate large query
results, so the SQL layer enforces a stable and visible ceiling.

---

## Data Source Setup

Use the built-in PostgreSQL connector in Looker Studio.

Connection requirements:
- host: Aiven public hostname
- port: Aiven PostgreSQL port
- database: reporting database (`dev-openjobseu` or `prod-openjobseu`)
- user: read-only reporting user such as `looker_ro`
- SSL: required

Recommended approach:
- create one Looker data source per reporting view
- avoid custom SQL inside Looker Studio
- keep the view definitions in PostgreSQL as the source of truth

---

## Report Structure

Recommended report pages:

### Overview
- scorecards from `vw_looker_audit_overview`
- source quality summary from `vw_looker_audit_source_7d`
- company quality summary from `vw_looker_audit_company_stats`

### Company Quality
- main table from `vw_looker_audit_company_stats`
- drill-down table from `vw_looker_audit_companies`
- filters: `legal_name`, `hq_country`, `ats_provider`, `is_active`

### Source Quality
- source summary from `vw_looker_audit_source_7d`
- weekly trend from `vw_looker_audit_source_trend`
- rejection breakdown from `vw_looker_audit_rejection_reasons`
- filters: `source`, `reason`, `week_start`

### ATS Health
- stale ATS table from `vw_looker_audit_ats_health`
- filters: `provider`, `legal_name`

---

## Aiven Security Checklist

Database-side:
- create a dedicated read-only user for Looker Studio
- grant `CONNECT` on the reporting database
- grant `USAGE` on schema `public`
- grant `SELECT` only on the `vw_looker_*` views
- do not reuse the runtime DB user

Network-side:
- keep SSL enabled
- allowlist the current Looker Studio PostgreSQL connector IP range in Aiven
- do not switch this service to private-only networking if Looker Studio must
  reach it directly

---

## Compatibility Notes

- Looker Studio documentation explicitly lists tested PostgreSQL versions only
  up to 14.
- Aiven may run PostgreSQL 15 or 16. Treat that as a practical-but-not-formally
  guaranteed compatibility point and verify the connector against the real
  cluster before sharing the report widely.

---

## Operational Notes

- The built-in `/internal/audit` panel remains the operational/internal tool.
- Looker Studio is the reporting surface only.
- If capped drill-down stops being sufficient, the next step should be a
  reporting-specific layer such as materialized views or a separate BI store,
  not widening free Looker Studio into full-history raw browsing.
