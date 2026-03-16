"""baseline

Revision ID: 56f2bf3724cd
Revises: 
Create Date: 2026-03-15 19:30:43.392750+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56f2bf3724cd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 001_initial_jobs.sql ---
    op.execute("""
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,

    source TEXT,
    source_job_id TEXT,
    source_url TEXT,

    title TEXT,
    company_name TEXT,
    description TEXT,

    remote_source_flag BOOLEAN,
    remote_scope TEXT,

    status TEXT,

    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    last_verified_at TIMESTAMPTZ,

    verification_failures INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ,

    remote_class TEXT,
    geo_class TEXT,

    policy_v1_decision TEXT,
    policy_v1_reason TEXT,

    policy_v2_decision TEXT,
    policy_v2_reason TEXT,

    compliance_status TEXT,
    compliance_score INTEGER,

    company_id UUID
);

CREATE INDEX idx_jobs_company_id ON jobs(company_id);
    """)

    # --- 002_companies.sql ---
    op.execute("""
CREATE TABLE companies (
    company_id UUID PRIMARY KEY,

    legal_name TEXT NOT NULL,
    brand_name TEXT,

    hq_country CHAR(2) NOT NULL,
    hq_city TEXT,

    eu_entity_verified BOOLEAN NOT NULL DEFAULT false,

    remote_posture TEXT NOT NULL CHECK (
        remote_posture IN ('REMOTE_ONLY', 'REMOTE_FRIENDLY', 'UNKNOWN')
    ),

    ats_provider TEXT,
    ats_slug TEXT,
    ats_api_url TEXT,
    careers_url TEXT,

    signal_score INTEGER NOT NULL DEFAULT 0,
    signal_last_computed_at TIMESTAMPTZ,

    approved_jobs_count INTEGER NOT NULL DEFAULT 0,
    last_approved_job_at TIMESTAMPTZ,

    is_active BOOLEAN NOT NULL DEFAULT true,
    bootstrap BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Case-insensitive uniqueness
CREATE UNIQUE INDEX idx_companies_legal_name_ci
ON companies (LOWER(legal_name));

CREATE INDEX idx_companies_active
ON companies (is_active);

-- FK dopiero po stworzeniu companies
ALTER TABLE jobs
ADD CONSTRAINT fk_jobs_company
FOREIGN KEY (company_id)
REFERENCES companies(company_id);
    """)

    # --- 003_ingestion_and_compliance.sql ---
    op.execute("""
BEGIN;

-- =========================================================
-- UUID defaults (no extension required)
-- =========================================================


-- =========================================================
-- 1. COMPANY ATS (multi-ATS support)
-- =========================================================

CREATE TABLE IF NOT EXISTS company_ats (
    company_ats_id UUID PRIMARY KEY DEFAULT (md5(random()::text || clock_timestamp()::text)::uuid),

    company_id UUID NOT NULL,

    provider TEXT NOT NULL,

    ats_slug TEXT,
    ats_api_url TEXT,
    careers_url TEXT,

    is_active BOOLEAN NOT NULL DEFAULT true,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_company_ats_company
        FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_company_ats_company
ON company_ats(company_id);

CREATE INDEX IF NOT EXISTS idx_company_ats_provider
ON company_ats(provider);


-- =========================================================
-- 2. JOBS TABLE EXTENSIONS
-- =========================================================

-- canonical company link
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS company_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_jobs_company'
          AND conrelid = 'jobs'::regclass
    ) THEN
        ALTER TABLE jobs
        ADD CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id)
        REFERENCES companies(company_id);
    END IF;
END
$$;


-- canonical job identity across sources
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS job_uid TEXT;

UPDATE jobs
SET job_uid = COALESCE(job_uid, job_id)
WHERE job_uid IS NULL;

ALTER TABLE jobs
ALTER COLUMN job_uid SET NOT NULL;


-- repost / duplicate detection
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS job_fingerprint TEXT;


-- raw ATS payload
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS source_payload JSONB;


-- schema drift detection
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS source_schema_hash TEXT;


-- policy version used for compliance
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS policy_version TEXT;


-- =========================================================
-- 3. INGESTION SAFETY CONSTRAINTS
-- =========================================================

-- protect against duplicate ingestion from same ATS
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'jobs_source_unique'
          AND conrelid = 'jobs'::regclass
    ) THEN
        ALTER TABLE jobs
        ADD CONSTRAINT jobs_source_unique
        UNIQUE (source, source_job_id);
    END IF;
END
$$;


-- =========================================================
-- 4. INDEXES FOR FEED + ANALYTICS
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_jobs_job_uid
ON jobs(job_uid);

CREATE INDEX IF NOT EXISTS idx_jobs_company
ON jobs(company_id);

CREATE INDEX IF NOT EXISTS idx_jobs_compliance_status
ON jobs(compliance_status);

CREATE INDEX IF NOT EXISTS idx_jobs_remote_class
ON jobs(remote_class);

CREATE INDEX IF NOT EXISTS idx_jobs_geo_class
ON jobs(geo_class);

CREATE INDEX IF NOT EXISTS idx_jobs_first_seen
ON jobs(first_seen_at);

CREATE INDEX IF NOT EXISTS idx_jobs_last_seen
ON jobs(last_seen_at);

-- feed query acceleration
CREATE INDEX IF NOT EXISTS idx_jobs_feed
ON jobs(compliance_status, last_seen_at DESC);

-- JSON payload queries
CREATE INDEX IF NOT EXISTS idx_jobs_payload_gin
ON jobs USING GIN (source_payload);


-- =========================================================
-- 5. COMPLIANCE REPORTS (decision engine output)
-- =========================================================

CREATE TABLE IF NOT EXISTS compliance_reports (
    report_id UUID PRIMARY KEY DEFAULT (md5(random()::text || clock_timestamp()::text)::uuid),

    job_id TEXT NOT NULL,

    policy_version TEXT NOT NULL,

    remote_class TEXT,
    geo_class TEXT,

    hard_geo_flag BOOLEAN,

    base_score INTEGER,

    penalties JSONB,
    bonuses JSONB,

    final_score INTEGER,
    final_status TEXT,

    decision_vector JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_compliance_reports_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(job_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_compliance_reports_job
ON compliance_reports(job_id);

CREATE INDEX IF NOT EXISTS idx_compliance_reports_status
ON compliance_reports(final_status);

CREATE INDEX IF NOT EXISTS idx_compliance_reports_policy
ON compliance_reports(policy_version);


-- =========================================================
-- 6. MIGRATE EXISTING ATS DATA FROM COMPANIES
-- =========================================================

INSERT INTO company_ats (
    company_id,
    provider,
    ats_slug,
    ats_api_url,
    careers_url,
    created_at,
    updated_at
)
SELECT
    c.company_id,
    c.ats_provider,
    c.ats_slug,
    c.ats_api_url,
    c.careers_url,
    c.created_at,
    c.updated_at
FROM companies c
LEFT JOIN company_ats ca
    ON ca.company_id = c.company_id
   AND ca.provider = c.ats_provider
   AND ca.ats_slug IS NOT DISTINCT FROM c.ats_slug
WHERE c.ats_provider IS NOT NULL
  AND ca.company_ats_id IS NULL;


COMMIT;
    """)

    # --- 004_jobs_feed_fast_index.sql ---
    op.execute("""
CREATE INDEX idx_jobs_feed_fast
ON jobs(last_seen_at DESC)
WHERE compliance_status = 'approved';
    """)

    # --- 005_job_sources_and_fingerprint_uniqueness.sql ---
    op.execute("""
-- =========================================================
-- 1. SOURCE MAPPING TABLE
-- =========================================================

CREATE TABLE IF NOT EXISTS job_sources (
    job_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    source_url TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_job_sources PRIMARY KEY (source, source_job_id),
    CONSTRAINT fk_job_sources_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(job_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_sources_job_id
ON job_sources(job_id);

CREATE INDEX IF NOT EXISTS idx_job_sources_source
ON job_sources(source);


-- =========================================================
-- 2. BACKFILL SOURCE MAPPINGS FROM LEGACY COLUMNS
-- =========================================================

INSERT INTO job_sources (
    job_id,
    source,
    source_job_id,
    source_url,
    first_seen_at,
    last_seen_at,
    created_at,
    updated_at
)
SELECT
    j.job_id,
    j.source,
    j.source_job_id,
    j.source_url,
    COALESCE(j.first_seen_at, NOW()),
    COALESCE(j.last_seen_at, NOW()),
    NOW(),
    NOW()
FROM jobs j
WHERE j.source IS NOT NULL
  AND btrim(j.source) <> ''
  AND j.source_job_id IS NOT NULL
  AND btrim(j.source_job_id) <> ''
ON CONFLICT (source, source_job_id) DO NOTHING;


-- =========================================================
-- 3. MOVE SOURCE UNIQUENESS FROM jobs TO job_sources
-- =========================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'jobs_source_unique'
          AND conrelid = 'jobs'::regclass
    ) THEN
        ALTER TABLE jobs DROP CONSTRAINT jobs_source_unique;
    END IF;
END
$$;


-- =========================================================
-- 4. ENFORCE NON-NULL + UNIQUE job_fingerprint
-- =========================================================

UPDATE jobs
SET job_fingerprint = md5(
    CONCAT(
        COALESCE(company_id::text, ''),
        '|',
        lower(regexp_replace(COALESCE(company_name, ''), '\s+', ' ', 'g')),
        '|',
        lower(regexp_replace(COALESCE(title, ''), '\s+', ' ', 'g')),
        '|',
        lower(regexp_replace(COALESCE(remote_scope, ''), '\s+', ' ', 'g')),
        '|',
        left(lower(regexp_replace(COALESCE(description, ''), '\s+', ' ', 'g')), 500)
    )
);

WITH duplicate_fingerprints AS (
    SELECT
        job_id,
        job_fingerprint,
        ROW_NUMBER() OVER (
            PARTITION BY job_fingerprint
            ORDER BY COALESCE(last_seen_at, first_seen_at, NOW()) DESC, job_id ASC
        ) AS row_num
    FROM jobs
)
UPDATE jobs j
SET job_fingerprint = md5(j.job_fingerprint || '|' || j.job_id)
FROM duplicate_fingerprints d
WHERE d.job_id = j.job_id
  AND d.row_num > 1;

ALTER TABLE jobs
ALTER COLUMN job_fingerprint SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_fingerprint_unique
ON jobs(job_fingerprint);
    """)

    # --- 006_normalize_job_fingerprint_md5.sql ---
    op.execute("""
-- Normalize fingerprint algorithm to md5 so schema bootstrap does not require
-- pgcrypto and all environments use the same dedup key format.
WITH canonical AS (
    SELECT
        j.job_id,
        md5(
            CONCAT(
                COALESCE(j.company_id::text, ''),
                '|',
                lower(regexp_replace(COALESCE(j.company_name, ''), '\s+', ' ', 'g')),
                '|',
                lower(regexp_replace(COALESCE(j.title, ''), '\s+', ' ', 'g')),
                '|',
                lower(regexp_replace(COALESCE(j.remote_scope, ''), '\s+', ' ', 'g')),
                '|',
                left(lower(regexp_replace(COALESCE(j.description, ''), '\s+', ' ', 'g')), 500)
            )
        ) AS canonical_fingerprint
    FROM jobs j
),
resolved AS (
    SELECT
        c.job_id,
        CASE
            WHEN ROW_NUMBER() OVER (
                PARTITION BY c.canonical_fingerprint
                ORDER BY COALESCE(j.last_seen_at, j.first_seen_at, NOW()) DESC, j.job_id ASC
            ) = 1
            THEN c.canonical_fingerprint
            ELSE md5(c.canonical_fingerprint || '|' || c.job_id)
        END AS new_fingerprint
    FROM canonical c
    JOIN jobs j ON j.job_id = c.job_id
)
UPDATE jobs j
SET job_fingerprint = r.new_fingerprint
FROM resolved r
WHERE r.job_id = j.job_id
  AND j.job_fingerprint IS DISTINCT FROM r.new_fingerprint;

ALTER TABLE jobs
ALTER COLUMN job_fingerprint SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_fingerprint_unique
ON jobs(job_fingerprint);
    """)

    # --- 007_company_ats_last_sync_at.sql ---
    op.execute("""
BEGIN;

ALTER TABLE company_ats
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;

COMMIT;
    """)

    # --- 008_compliance_reports_unique_index.sql ---
    op.execute("""
BEGIN;

-- Add job_uid to compliance_reports to allow canonical uniqueness checks
ALTER TABLE compliance_reports 
ADD COLUMN IF NOT EXISTS job_uid TEXT;

-- Backfill job_uid from jobs table
UPDATE compliance_reports cr
SET job_uid = j.job_uid
FROM jobs j
WHERE j.job_id = cr.job_id
AND cr.job_uid IS NULL;

-- Make it NOT NULL for the index
-- Note: if there are orphans (shouldn't be), this might fail, 
-- but compliance_reports has a FK to jobs.
ALTER TABLE compliance_reports 
ALTER COLUMN job_uid SET NOT NULL;

-- Add unique index as requested
CREATE UNIQUE INDEX IF NOT EXISTS idx_compliance_report_unique
ON compliance_reports(job_uid, policy_version);

COMMIT;
    """)

    # --- 009_job_taxonomy_columns.sql ---
    op.execute("""
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_family TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_role TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS seniority TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS specialization TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_quality_score INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_jobs_specialization
ON jobs (job_family, specialization, seniority);

CREATE INDEX IF NOT EXISTS idx_jobs_quality_score
ON jobs (job_quality_score);
    """)

    # --- 010_availability_status_column.sql ---
    op.execute("""
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS availability_status VARCHAR(50);
    """)

    # --- 011_add_salary_fields.sql ---
    op.execute("""
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_min REAL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_max REAL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(10);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_period VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_source VARCHAR(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_min_eur REAL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_max_eur REAL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_transparency_status TEXT;
    """)

    # --- 012_salary_parsing_cases.sql ---
    op.execute("""
-- 012_salary_parsing_cases.sql
CREATE TABLE IF NOT EXISTS salary_parsing_cases (
    id SERIAL PRIMARY KEY,
    source TEXT,
    job_id TEXT,
    salary_raw TEXT,
    description_fragment TEXT,
    parser_min INTEGER,
    parser_max INTEGER,
    parser_currency TEXT,
    parser_confidence REAL,
    status TEXT DEFAULT 'needs_review',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_salary_cases_status ON salary_parsing_cases(status);
    """)

    # --- 013_update_salary_fields_to_integer.sql ---
    op.execute("""
-- 013_update_salary_fields_to_integer.sql

ALTER TABLE jobs
ALTER COLUMN salary_min TYPE INTEGER USING salary_min::INTEGER,
ALTER COLUMN salary_max TYPE INTEGER USING salary_max::INTEGER,
ADD COLUMN IF NOT EXISTS salary_confidence INTEGER DEFAULT 0;

ALTER TABLE salary_parsing_cases
ALTER COLUMN parser_min TYPE INTEGER USING parser_min::INTEGER,
ALTER COLUMN parser_max TYPE INTEGER USING parser_max::INTEGER,
ALTER COLUMN parser_confidence TYPE INTEGER USING parser_confidence::INTEGER;
    """)

    # --- 014_job_snapshots.sql ---
    op.execute("""
CREATE TABLE IF NOT EXISTS job_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,

    job_id TEXT NOT NULL,
    job_fingerprint TEXT NOT NULL,

    title TEXT,
    company_name TEXT,

    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,

    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_snapshots_job_id
ON job_snapshots(job_id);

CREATE INDEX IF NOT EXISTS idx_job_snapshots_captured_at
ON job_snapshots(captured_at);
    """)

    # --- 015_companies_discovery_last_checked_at.sql ---
    op.execute("""
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS discovery_last_checked_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_companies_discovery_last_checked_at
ON companies (discovery_last_checked_at);
    """)

    # --- 016_companies_index_provider_ats_slug.sql ---
    op.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_ats_provider_slug
ON company_ats(provider, ats_slug);
    """)

    # --- 017_job_sources_seen_count.sql ---
    op.execute("""
ALTER TABLE job_sources
ADD COLUMN IF NOT EXISTS seen_count INTEGER NOT NULL DEFAULT 1;
    """)

    # --- 018_jobs_repost_markers.sql ---
    op.execute("""
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS is_repost BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS repost_count INTEGER NOT NULL DEFAULT 0;
    """)

    # --- 019_market_daily_stats.sql ---
    op.execute("""
CREATE TABLE IF NOT EXISTS market_daily_stats (
    date DATE PRIMARY KEY,

    jobs_created INTEGER NOT NULL,
    jobs_expired INTEGER NOT NULL,
    jobs_active INTEGER NOT NULL,
    jobs_reposted INTEGER NOT NULL,

    avg_salary_eur NUMERIC,
    median_salary_eur NUMERIC,

    avg_job_lifetime INTERVAL,

    remote_ratio NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_market_daily_stats_date
ON market_daily_stats(date);
    """)

    # --- 020_market_daily_stats_segments.sql ---
    op.execute("""
CREATE TABLE IF NOT EXISTS market_daily_stats_segments (
    date DATE NOT NULL,

    segment_type TEXT NOT NULL,
    segment_value TEXT NOT NULL,

    jobs_active INTEGER NOT NULL,
    jobs_created INTEGER NOT NULL,

    avg_salary_eur NUMERIC,
    median_salary_eur NUMERIC,

    PRIMARY KEY (date, segment_type, segment_value)
);

CREATE INDEX IF NOT EXISTS idx_market_segments_date
ON market_daily_stats_segments(date);
    """)

    # --- 021_indexes_on_jobs.sql ---
    op.execute("""
CREATE INDEX IF NOT EXISTS idx_jobs_active_market
ON jobs (first_seen_at)
WHERE availability_status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_active_salary
ON jobs (salary_min_eur)
WHERE availability_status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_active_taxonomy
ON jobs (job_family, seniority)
WHERE availability_status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_active_dataset
ON jobs (first_seen_at, salary_min_eur)
WHERE availability_status = 'active';
    """)

    # --- 022_split_discovery_timestamps.sql ---
    op.execute("""
-- 1. Dodanie nowych kolumn do niezależnego śledzenia etapów
ALTER TABLE companies ADD COLUMN IF NOT EXISTS careers_last_checked_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS ats_guess_last_checked_at TIMESTAMP WITH TIME ZONE;

-- 2. Migracja dotychczasowego stanu (jeśli firma była skanowana wcześniej)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'companies' AND column_name = 'discovery_last_checked_at'
    ) THEN
        EXECUTE 'UPDATE companies 
                 SET careers_last_checked_at = discovery_last_checked_at,
                     ats_guess_last_checked_at = discovery_last_checked_at
                 WHERE discovery_last_checked_at IS NOT NULL';
    END IF;
END $$;

-- 3. Usunięcie przestarzałej kolumny
ALTER TABLE companies DROP COLUMN IF EXISTS discovery_last_checked_at;

-- 4. Utworzenie zoptymalizowanych, częściowych indeksów pod warunki zapytania
-- Worker: careers_crawler
CREATE INDEX IF NOT EXISTS idx_companies_careers_check 
ON companies (careers_last_checked_at ASC NULLS FIRST) 
WHERE bootstrap = FALSE 
  AND is_active = TRUE 
  AND ats_provider IS NULL 
  AND careers_url IS NOT NULL;

-- Worker: ats_guessing
CREATE INDEX IF NOT EXISTS idx_companies_ats_guess_check 
ON companies (ats_guess_last_checked_at ASC NULLS FIRST) 
WHERE bootstrap = FALSE 
  AND is_active = TRUE 
  AND ats_provider IS NULL 
  AND careers_url IS NOT NULL;
    """)

    # --- 023_add_source_department.sql ---
    op.execute("""
-- Add column to store the raw department/category extracted directly from the ATS API
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_department VARCHAR(255);
    """)

    # --- 024_company_job_stats.sql ---
    op.execute("""
-- Add aggregated job statistics columns to the companies table

ALTER TABLE companies ADD COLUMN IF NOT EXISTS total_jobs_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS rejected_jobs_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_active_job_at TIMESTAMP WITH TIME ZONE;
    """)



def downgrade() -> None:
    pass