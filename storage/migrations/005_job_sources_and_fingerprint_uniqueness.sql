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
SET job_fingerprint = encode(
    digest(
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
        ),
        'sha256'
    ),
    'hex'
)
WHERE job_fingerprint IS NULL
   OR btrim(job_fingerprint) = '';

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
SET job_fingerprint = encode(digest(j.job_fingerprint || '|' || j.job_id, 'sha256'), 'hex')
FROM duplicate_fingerprints d
WHERE d.job_id = j.job_id
  AND d.row_num > 1;

ALTER TABLE jobs
ALTER COLUMN job_fingerprint SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_fingerprint_unique
ON jobs(job_fingerprint);
