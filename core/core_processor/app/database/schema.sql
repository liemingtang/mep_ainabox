-- Database schema for Modular Document Intelligence System (MDIS)
-- This script creates all necessary tables for the core system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table - Core document metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    source VARCHAR(100),
    processing_status VARCHAR(50) DEFAULT 'pending',
    document_type VARCHAR(50),
    company VARCHAR(255),
    year INTEGER,
    metadata JSONB DEFAULT '{}',
    -- New fields for data source tracking
    original_file_path VARCHAR(500),  -- Original local file system path
    data_source_type VARCHAR(100),    -- Type of data source (file_system, api, database, etc.)
    data_source_uri VARCHAR(500),     -- URI/URL of the data source
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT
);

-- Processing jobs table - Track processing workflow
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_data JSONB DEFAULT '{}',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document content table - Extracted text and content
CREATE TABLE IF NOT EXISTS document_content (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    text_content TEXT,
    extracted_tables JSONB DEFAULT '[]',
    layout_info JSONB DEFAULT '{}',
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document embeddings table - Vector embeddings for semantic search
CREATE TABLE IF NOT EXISTS document_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    embedding_vector REAL[] NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document entities table - Extracted entities
CREATE TABLE IF NOT EXISTS document_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL,
    entity_value TEXT NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    start_position INTEGER,
    end_position INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document relationships table - Relationships between documents
CREATE TABLE IF NOT EXISTS document_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(3,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Climate data table - Climate analysis results
CREATE TABLE IF NOT EXISTS climate_data (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    emissions JSONB DEFAULT '[]',
    targets JSONB DEFAULT '[]',
    risks JSONB DEFAULT '[]',
    governance JSONB DEFAULT '{}',
    strategy JSONB DEFAULT '{}',
    compliance JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Financial data table - Financial analysis results
CREATE TABLE IF NOT EXISTS financial_data (
    document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    income_statement JSONB DEFAULT '{}',
    balance_sheet JSONB DEFAULT '{}',
    cash_flow JSONB DEFAULT '{}',
    ratios JSONB DEFAULT '{}',
    trends JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing results table - Detailed processing results
CREATE TABLE IF NOT EXISTS processing_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    processing_step VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    result_data JSONB DEFAULT '{}',
    error_message TEXT,
    processing_time DECIMAL(10,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table - User management
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table - Session management
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log table - System audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration table - Runtime configuration
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_company ON documents(company);
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_model ON document_embeddings(embedding_model);

CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_document_entities_type ON document_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_document_entities_value ON document_entities(entity_value);

CREATE INDEX IF NOT EXISTS idx_document_relationships_source ON document_relationships(source_document_id);
CREATE INDEX IF NOT EXISTS idx_document_relationships_target ON document_relationships(target_document_id);
CREATE INDEX IF NOT EXISTS idx_document_relationships_type ON document_relationships(relationship_type);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_documents_filename_fts ON documents USING gin(to_tsvector('english', filename));
CREATE INDEX IF NOT EXISTS idx_document_content_text_fts ON document_content USING gin(to_tsvector('english', text_content));

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
('processing', '{"max_file_size": "100MB", "supported_formats": ["pdf", "docx", "txt", "html"], "parallel_processing": true}', 'Processing configuration'),
('storage', '{"backup_enabled": true, "retention_days": 30}', 'Storage configuration'),
('security', '{"jwt_expiry_hours": 24, "password_min_length": 8}', 'Security configuration')
ON CONFLICT (key) DO NOTHING;

-- Create views for common queries
CREATE OR REPLACE VIEW document_summary AS
SELECT 
    d.id,
    d.filename,
    d.document_type,
    d.company,
    d.year,
    d.processing_status,
    d.created_at,
    d.processed_at,
    COUNT(pj.id) as total_jobs,
    COUNT(CASE WHEN pj.status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN pj.status = 'failed' THEN 1 END) as failed_jobs
FROM documents d
LEFT JOIN processing_jobs pj ON d.id = pj.document_id
GROUP BY d.id, d.filename, d.document_type, d.company, d.year, d.processing_status, d.created_at, d.processed_at;

CREATE OR REPLACE VIEW processing_stats AS
SELECT 
    job_type,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MIN(created_at) as first_job,
    MAX(created_at) as last_job
FROM processing_jobs
GROUP BY job_type, status;

-- Create functions for common operations
CREATE OR REPLACE FUNCTION update_document_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update timestamps
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_updated_at();

CREATE TRIGGER update_climate_data_updated_at
    BEFORE UPDATE ON climate_data
    FOR EACH ROW
    EXECUTE FUNCTION update_document_updated_at();

CREATE TRIGGER update_financial_data_updated_at
    BEFORE UPDATE ON financial_data
    FOR EACH ROW
    EXECUTE FUNCTION update_document_updated_at();

-- Function to clean up old sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get document processing timeline
CREATE OR REPLACE FUNCTION get_document_timeline(document_uuid UUID)
RETURNS TABLE(
    step VARCHAR(50),
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10,3)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pj.job_type as step,
        pj.status,
        pj.started_at,
        pj.completed_at,
        EXTRACT(EPOCH FROM (pj.completed_at - pj.started_at)) as duration_seconds
    FROM processing_jobs pj
    WHERE pj.document_id = document_uuid
    ORDER BY pj.created_at;
END;
$$ LANGUAGE plpgsql; 