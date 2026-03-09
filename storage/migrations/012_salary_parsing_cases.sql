-- 012_salary_parsing_cases.sql
CREATE TABLE IF NOT EXISTS salary_parsing_cases (
    id SERIAL PRIMARY KEY,
    source TEXT,
    job_id TEXT,
    salary_raw TEXT,
    description_fragment TEXT,
    parser_min INTEGER,
    parser_max INTEGER,
    parser_currency TEXT,
    parser_confidence REAL,
    status TEXT DEFAULT 'needs_review',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_salary_cases_status ON salary_parsing_cases(status);
