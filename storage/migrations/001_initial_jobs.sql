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
