CREATE UNIQUE INDEX IF NOT EXISTS idx_company_ats_provider_slug
ON company_ats(provider, ats_slug);
