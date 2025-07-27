# Data Source Tracking Feature

## Overview

The MEP AI Box system now includes comprehensive data source tracking capabilities. This feature allows the system to maintain information about the original location of files and data sources, even when files are processed through dockerized containers that mount local folders.

## Key Features

### 1. Original File Path Preservation
- **Problem Solved**: When files are uploaded through dockerized containers, the system converts local file paths to container paths (e.g., `/media/lie/DATA2/ai_scan_folder/file.pdf` → `/app/scan_folder/file.pdf`)
- **Solution**: The system now preserves the original local file system path in addition to the container path used for processing
- **Benefit**: Users can always trace back to the original file location on their local system

### 2. Data Source Type Classification
- **Purpose**: Categorize different types of data sources for future extensibility
- **Current Types**:
  - `file_system`: Local files and folders
  - Future types: `api`, `database`, `web_scraper`, `email`, etc.
- **Benefit**: Enables future features like data source-specific processing rules

### 3. Data Source URI/URL Tracking
- **Purpose**: Store the complete URI or URL of the data source
- **For File System**: Contains the full local file path
- **Future Use**: Will support URLs, API endpoints, database connections, etc.

## Database Schema Changes

### New Columns Added to `documents` Table

```sql
-- Original local file system path before container path conversion
original_file_path VARCHAR(500)

-- Type of data source (file_system, api, database, etc.)
data_source_type VARCHAR(100)

-- URI/URL of the data source
data_source_uri VARCHAR(500)
```

### Indexes Created

```sql
CREATE INDEX idx_documents_original_file_path ON documents(original_file_path);
CREATE INDEX idx_documents_data_source_type ON documents(data_source_type);
CREATE INDEX idx_documents_data_source_uri ON documents(data_source_uri);
```

## Implementation Details

### 1. Folder Scanner Updates
The `folder_scanner.py` now captures the original file path before any container path conversion:

```python
# Store the original file path before any container path conversion
original_file_path = file_path

# Convert to container path for processing
if '/media/lie/DATA2/ai_scan_folder' in file_path:
    container_file_path = file_path.replace('/media/lie/DATA2/ai_scan_folder', '/app/scan_folder')
    file_path = container_file_path

# Include both paths in metadata
metadata = {
    "file_path": file_path,  # Container path for processing
    "original_file_path": original_file_path,  # Original local path
    "data_source_type": "file_system",
    "data_source_uri": original_file_path
}
```

### 2. Document Model Updates
The `DocumentMetadata` model now includes the new fields:

```python
class DocumentMetadata(BaseModel):
    # ... existing fields ...
    original_file_path: Optional[str] = None
    data_source_type: Optional[str] = None
    data_source_uri: Optional[str] = None
```

### 3. Database Service Updates
The document service has been updated to handle the new fields in both PostgreSQL and Elasticsearch storage.

## Migration Guide

### Running the Migration

1. **Ensure the database is running**:
   ```bash
   cd mep_ainabox
   docker compose up -d postgres
   ```

2. **Run the migration script**:
   ```bash
   cd core/core_processor
   ./run_migration.sh
   ```

3. **Verify the migration**:
   The script will show a summary of the changes and verify that all documents have been updated.

### Migration Details

The migration script will:
- Add the new columns to the `documents` table
- Create indexes for better query performance
- Update existing documents with default values:
  - `original_file_path` = current `file_path`
  - `data_source_type` = `'file_system'`
  - `data_source_uri` = current `file_path`

## Dashboard Integration

### Document Details View
The dashboard now displays:
- **Original Path**: The local file system path before container conversion
- **Data Source Type**: Badge showing the type of data source
- **Data Source URI**: The complete URI/URL of the data source

### Document List View
The documents table now shows:
- Data source type badges
- Truncated original file paths for quick reference

## Future Extensibility

### Planned Data Source Types

1. **API Endpoints**
   - `data_source_type`: `api`
   - `data_source_uri`: `https://api.example.com/data`

2. **Database Connections**
   - `data_source_type`: `database`
   - `data_source_uri`: `postgresql://user:pass@host:port/db`

3. **Web Scraping**
   - `data_source_type`: `web_scraper`
   - `data_source_uri`: `https://example.com/page`

4. **Email Attachments**
   - `data_source_type`: `email`
   - `data_source_uri`: `imap://user:pass@mail.example.com`

5. **Cloud Storage**
   - `data_source_type`: `cloud_storage`
   - `data_source_uri`: `s3://bucket/path/to/file`

### Benefits for Future Development

1. **Unified Data Source Interface**: All data sources can be handled through a common interface
2. **Source-Specific Processing**: Different processing rules based on data source type
3. **Audit Trail**: Complete traceability of data origins
4. **Data Lineage**: Track how data flows through the system
5. **Compliance**: Support for data governance and compliance requirements

## API Changes

### Document Upload Response
The document upload API now returns additional fields:

```json
{
  "document_id": "uuid",
  "processing_job_id": "uuid",
  "status": "processing",
  "message": "Document uploaded and processing started",
  "original_file_path": "/media/lie/DATA2/ai_scan_folder/document.pdf",
  "data_source_type": "file_system",
  "data_source_uri": "/media/lie/DATA2/ai_scan_folder/document.pdf"
}
```

### Document Retrieval
When retrieving documents, the new fields are included:

```json
{
  "id": "uuid",
  "filename": "document.pdf",
  "file_path": "/app/scan_folder/document.pdf",
  "original_file_path": "/media/lie/DATA2/ai_scan_folder/document.pdf",
  "data_source_type": "file_system",
  "data_source_uri": "/media/lie/DATA2/ai_scan_folder/document.pdf",
  // ... other fields
}
```

## Troubleshooting

### Common Issues

1. **Migration Fails**: Ensure PostgreSQL is running and accessible
2. **Missing Data**: Check that the folder scanner is using the updated code
3. **Dashboard Not Showing Data**: Verify that the dashboard JavaScript has been updated

### Verification Commands

Check if the migration was successful:

```sql
-- Check if new columns exist
\d documents

-- Check if data is populated
SELECT COUNT(*) as total_documents,
       COUNT(original_file_path) as with_original_path,
       COUNT(data_source_type) as with_source_type
FROM documents;
```

## Conclusion

The data source tracking feature provides a solid foundation for handling diverse data sources while maintaining the current dockerized processing workflow. It ensures that users can always trace back to the original location of their files while enabling future extensibility for other data source types. 