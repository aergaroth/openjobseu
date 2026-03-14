-- 1. Dodanie nowych kolumn do niezależnego śledzenia etapów
ALTER TABLE companies ADD COLUMN careers_last_checked_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE companies ADD COLUMN ats_guess_last_checked_at TIMESTAMP WITH TIME ZONE;

-- 2. Migracja dotychczasowego stanu (jeśli firma była skanowana wcześniej)
UPDATE companies 
SET 
    careers_last_checked_at = discovery_last_checked_at,
    ats_guess_last_checked_at = discovery_last_checked_at
WHERE discovery_last_checked_at IS NOT NULL;

-- 3. Usunięcie przestarzałej kolumny
ALTER TABLE companies DROP COLUMN discovery_last_checked_at;

-- 4. Utworzenie zoptymalizowanych, częściowych indeksów pod warunki zapytania
-- Worker: careers_crawler
CREATE INDEX idx_companies_careers_check 
ON companies (careers_last_checked_at ASC NULLS FIRST) 
WHERE bootstrap = FALSE 
  AND is_active = TRUE 
  AND ats_provider IS NULL 
  AND careers_url IS NOT NULL;

-- Worker: ats_guessing
CREATE INDEX idx_companies_ats_guess_check 
ON companies (ats_guess_last_checked_at ASC NULLS FIRST) 
WHERE bootstrap = FALSE 
  AND is_active = TRUE 
  AND ats_provider IS NULL 
  AND careers_url IS NOT NULL;