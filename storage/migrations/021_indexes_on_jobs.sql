CREATE INDEX IF NOT EXISTS idx_jobs_active_market
ON jobs (first_seen_at)
WHERE availability_status = 'active';

CREATE INDEX IF NOT EXISTS idx_jobs_active_salary
ON jobs (salary_min_eur)
WHERE availability_status = 'active';

CREATE INDEX idx_jobs_active_taxonomy
ON jobs (job_family, seniority)
WHERE availability_status = 'active';

CREATE INDEX CONCURRENTLY idx_jobs_active_dataset
ON jobs (first_seen_at, salary_min_eur)
WHERE availability_status = 'active';