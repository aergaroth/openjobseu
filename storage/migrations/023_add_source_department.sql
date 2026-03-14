-- Add column to store the raw department/category extracted directly from the ATS API
ALTER TABLE jobs ADD COLUMN source_department VARCHAR(255);