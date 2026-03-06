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
