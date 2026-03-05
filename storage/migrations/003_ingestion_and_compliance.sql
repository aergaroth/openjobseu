BEGIN;

-- =========================================================
-- EXTENSION (required for UUID generation)
-- =========================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =========================================================
-- 1. COMPANY ATS (multi-ATS support)
-- =========================================================

CREATE TABLE IF NOT EXISTS company_ats (
    company_ats_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

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
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

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
