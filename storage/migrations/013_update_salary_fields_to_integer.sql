-- 013_update_salary_fields_to_integer.sql

ALTER TABLE jobs
ALTER COLUMN salary_min TYPE INTEGER USING salary_min::INTEGER,
ALTER COLUMN salary_max TYPE INTEGER USING salary_max::INTEGER,
ADD COLUMN IF NOT EXISTS salary_confidence INTEGER DEFAULT 0;

ALTER TABLE salary_parsing_cases
ALTER COLUMN parser_min TYPE INTEGER USING parser_min::INTEGER,
ALTER COLUMN parser_max TYPE INTEGER USING parser_max::INTEGER,
ALTER COLUMN parser_confidence TYPE INTEGER USING parser_confidence::INTEGER;
