CREATE INDEX idx_jobs_feed_fast
ON jobs(last_seen_at DESC)
WHERE compliance_status = 'approved';
