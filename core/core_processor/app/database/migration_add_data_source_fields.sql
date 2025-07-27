-- Migration script to add data source tracking fields to existing documents table
-- Run this script to update existing databases

-- Add new columns for data source tracking
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS original_file_path VARCHAR(500),
ADD COLUMN IF NOT EXISTS data_source_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS data_source_uri VARCHAR(500);

-- Add indexes for the new fields for better query performance
CREATE INDEX IF NOT EXISTS idx_documents_original_file_path ON documents(original_file_path);
CREATE INDEX IF NOT EXISTS idx_documents_data_source_type ON documents(data_source_type);
CREATE INDEX IF NOT EXISTS idx_documents_data_source_uri ON documents(data_source_uri);

-- Update existing documents to have default values for the new fields
-- For existing documents, we'll set the original_file_path to the current file_path
-- and data_source_type to 'file_system' as a reasonable default
UPDATE documents 
SET 
    original_file_path = file_path,
    data_source_type = 'file_system',
    data_source_uri = file_path
WHERE original_file_path IS NULL;

-- Add comments to document the new fields
COMMENT ON COLUMN documents.original_file_path IS 'Original local file system path before container path conversion';
COMMENT ON COLUMN documents.data_source_type IS 'Type of data source (file_system, api, database, etc.)';
COMMENT ON COLUMN documents.data_source_uri IS 'URI/URL of the data source';

-- Verify the migration
SELECT 
    COUNT(*) as total_documents,
    COUNT(original_file_path) as documents_with_original_path,
    COUNT(data_source_type) as documents_with_source_type,
    COUNT(data_source_uri) as documents_with_source_uri
FROM documents; 