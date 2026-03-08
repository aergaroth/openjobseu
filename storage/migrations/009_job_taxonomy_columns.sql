ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_family TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_role TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS seniority TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS specialization TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_quality_score INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_jobs_specialization
ON jobs (job_family, specialization, seniority);

CREATE INDEX IF NOT EXISTS idx_jobs_quality_score
ON jobs (job_quality_score);
