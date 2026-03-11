ALTER TABLE companies
ADD COLUMN discovery_last_checked_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_companies_discovery_last_checked_at
ON companies (discovery_last_checked_at);