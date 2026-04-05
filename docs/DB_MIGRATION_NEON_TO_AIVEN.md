# Aiven PostgreSQL Migration Notes

## Scope

This document captures the migration pattern that was used to move OpenJobsEU
from Neon to Aiven PostgreSQL.

It is meant as an operational reference for:
- rebuilding an environment from scratch
- cloning `prod` into a new database
- repeating the same workflow for future PostgreSQL moves

Current state:
- `dev` runs on Aiven PostgreSQL
- `prod` runs on Aiven PostgreSQL

The application model behind this playbook is simple:
- runtime uses `DB_MODE=standard`
- database access comes from `DATABASE_URL`
- auth is handled in the FastAPI app, not inside PostgreSQL
- the app does not depend on `pg_session_jwt` or PostgREST

---

## What Worked Well

The cleanest workflow was:
- create a brand new empty database on Aiven
- create a dedicated app user for that database
- grant that user `CREATE` on schema `public`
- enable `pg_trgm`
- restore a custom-format dump with a filtered restore list
- point the app at the new `DATABASE_URL`
- verify `/health`, `/ready`, and the built-in audit panel

The key lesson is that restore should go into a truly empty target. If tables,
indexes, or constraints already exist, `pg_restore` becomes noisy very quickly
with duplicate and already-exists errors.

---

## Legacy Objects to Ignore

Some historical Neon dumps may contain leftover objects unrelated to this app,
for example:

- `EXTENSION pg_session_jwt`
- `COMMENT ON EXTENSION pg_session_jwt`
- `SCHEMA pgrst`
- `FUNCTION pgrst.pre_config`

Those are not runtime dependencies for OpenJobsEU and should be filtered out
instead of recreated on Aiven.

The helper for this lives here:
- [scripts/filter_pg_restore_list.py]

---

## Migration Checklist

### 1. Create the dump from Neon

```bash
pg_dump -Fc --no-owner --no-privileges -d "$URL_DO_NEON_TECH" > moja_baza.dump
```

This dump should be treated as the migration backup for the whole window.

### 2. Generate the restore list

```bash
pg_restore -l moja_baza.dump > dump.list
```

### 3. Filter legacy objects

```bash
python scripts/filter_pg_restore_list.py dump.list -o dump.filtered.list
```

Optional sanity check:

```bash
grep -nE "pg_session_jwt|pgrst" dump.list
grep -nE "pg_session_jwt|pgrst" dump.filtered.list
```

The filtered file should not contain matches.

### 4. Prepare a fresh Aiven target

Before restore, prepare the destination:
- create a new empty database
- create a dedicated login/user for that database
- grant `CREATE` on schema `public`
- enable `pg_trgm`

Minimal SQL checklist:

```sql
GRANT CREATE ON SCHEMA public TO "app-dbuser";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Confirm the database is empty:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public';
```

If application tables are already there, stop and use a new empty database.

### 5. Restore to Aiven

```bash
pg_restore \
  --use-list=dump.filtered.list \
  --no-owner \
  -d "$URL_AIVEN" \
  moja_baza.dump
```

This workflow assumes:
- no `--clean`
- no `--create`
- no restore into a partially populated target

### 6. Verify the restored database

Check the extension list and confirm that `pgrst` is absent:

```sql
SELECT extname FROM pg_extension ORDER BY extname;

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'pgrst';
```

Check the core tables:

```sql
SELECT COUNT(*) FROM alembic_version;
SELECT COUNT(*) FROM jobs;
SELECT COUNT(*) FROM companies;
```

For production moves, it is worth comparing a few high-signal tables on both
sides, for example:
- `jobs`
- `companies`
- `company_ats`
- `compliance_reports`

### 7. Smoke check the app

Point the runtime to Aiven:

```bash
export DB_MODE=standard
export DATABASE_URL='postgresql+psycopg://...'
```

Then run a short smoke check:
1. start the app
2. check `/health`
3. check `/ready`
4. open `/internal/audit`
5. optionally run a maintenance tick once the environment is meant to be live

Useful repo helpers:
- `python scripts/db_smoke_check.py`
- `python scripts/post_deploy_smoke_check.py`

---

## Common Failure Modes

### `extension "pg_session_jwt" is not available`

Usually means the restore list still contains legacy entries that should have
been filtered out.

### `schema already exists`, `duplicate key`, `multiple primary keys`

Almost always means restore was pointed at a non-empty database.

### `permission denied for schema public`

The target app user is missing `CREATE` on `public`.

### `pg_trgm` errors

`pg_trgm` is a real dependency of this repository and should be enabled before
application cutover.

---

## Done Definition

Treat the migration as complete when:
- restore finishes without legacy-object or duplicate-object failures
- application data is present on Aiven
- `pg_session_jwt` and `pgrst` are absent from the target
- the application starts on the new `DATABASE_URL`
- `/health` and `/ready` return success
- the internal audit panel loads normally

---

## Notes for Future Moves

- A dedicated database user per environment worked better than reusing a broad
  admin login for application traffic.
- `pg_restore --role=...` was not needed in the successful Aiven workflow.
- Filtering `pg_session_jwt` and `pgrst` is safe for this repo because the app
  does not use those objects.
- For OpenJobsEU, the fastest confidence signal after cutover was:
  row-count comparison + `/health` + `/ready` + one audit-panel check.
