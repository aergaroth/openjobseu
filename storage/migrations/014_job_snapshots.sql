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