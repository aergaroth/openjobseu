CREATE TABLE companies (
    company_id UUID PRIMARY KEY,

    legal_name TEXT NOT NULL,
    brand_name TEXT,

    hq_country CHAR(2) NOT NULL,
    hq_city TEXT,

    eu_entity_verified BOOLEAN NOT NULL DEFAULT false,

    remote_posture TEXT NOT NULL CHECK (
        remote_posture IN ('REMOTE_ONLY', 'REMOTE_FRIENDLY', 'UNKNOWN')
    ),

    ats_provider TEXT,
    ats_slug TEXT,
    ats_api_url TEXT,
    careers_url TEXT,

    signal_score INTEGER NOT NULL DEFAULT 0,
    signal_last_computed_at TIMESTAMPTZ,

    approved_jobs_count INTEGER NOT NULL DEFAULT 0,
    last_approved_job_at TIMESTAMPTZ,

    is_active BOOLEAN NOT NULL DEFAULT true,
    bootstrap BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Case-insensitive uniqueness
CREATE UNIQUE INDEX idx_companies_legal_name_ci
ON companies (LOWER(legal_name));

CREATE INDEX idx_companies_active
ON companies (is_active);

-- FK dopiero po stworzeniu companies
ALTER TABLE jobs
ADD CONSTRAINT fk_jobs_company
FOREIGN KEY (company_id)
REFERENCES companies(company_id);
