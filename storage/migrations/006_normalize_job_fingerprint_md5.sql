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
