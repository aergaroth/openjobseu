-- Add aggregated job statistics columns to the companies table

ALTER TABLE companies ADD COLUMN IF NOT EXISTS total_jobs_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS rejected_jobs_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_active_job_at TIMESTAMP WITH TIME ZONE;