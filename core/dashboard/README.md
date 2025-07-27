# MDIS Dashboard

A comprehensive web-based monitoring and analytics dashboard for the Modular Document Intelligence System (MDIS).

## 🎯 Features

### Real-time Monitoring
- **System Health**: Monitor the status of all processing services
- **Document Processing**: Track file processing status from scan folder and file watcher
- **Pipeline Status**: View the status of each processing step
- **Storage Analytics**: Monitor Elasticsearch and Qdrant statistics

### Document Management
- **Recent Documents**: View the 10 most recent processed documents
- **Processing Status**: Real-time updates on document processing
- **Detailed Views**: Click to see comprehensive document information
- **Source Tracking**: Distinguish between scan folder and file watcher sources

### Scan Folder Management
- **Folder Scanning**: Scan any folder on the system for document processing
- **Real-time Progress**: Monitor scan progress with live updates
- **File Preview**: Preview folder structure before processing
- **Execution History**: Track all scan folder executions
- **Error Handling**: Comprehensive error reporting and recovery

### System Analytics
- **Service Health**: Response times and status for all services
- **Processing Pipeline**: Visual representation of processing steps
- **Storage Statistics**: Document counts in Elasticsearch and Qdrant
- **Error Tracking**: Monitor failed processing attempts

## 🚀 Quick Start

### Using Docker Compose (Recommended)
```bash
# Start the dashboard with all services
cd /path/to/mep_ainabox/core
docker-compose up -d dashboard

# Access the dashboard
open http://localhost:8010
```

## 📊 Dashboard Sections

### 1. Statistics Cards
- **Total Documents**: Count of all documents in the system
- **Processing**: Number of documents currently being processed
- **Completed**: Number of successfully processed documents
- **Failed**: Number of documents that failed processing

### 2. System Health
Real-time status of all services:
- Core Processor
- File Watcher
- Storage Manager
- Text Processor
- Metadata Processor
- Embedding Processor
- Entity Processor
- Processing Pipeline
- Document Router
- API Gateway
- Elasticsearch
- Qdrant
- Neo4j

### 3. Recent Documents Table
- **Filename**: Document name and type
- **Source**: Scan folder or file watcher
- **Status**: Processing, completed, failed, or pending
- **Size**: File size in human-readable format
- **Created**: Timestamp of document creation
- **Actions**: View detailed information

### 4. Storage Statistics
- **Elasticsearch Documents**: Total indexed documents
- **Qdrant Collections**: Number of vector collections

### 5. Processing Pipeline
Visual status of each processing step:
- Text Extraction
- Metadata Extraction
- Embedding Generation
- Entity Extraction
- Pipeline Orchestration

## 🔍 Scan Folder Functionality

### Overview
The scan folder feature allows you to process documents from any folder on your system. It provides a comprehensive interface for:

- **Folder Selection**: Browse and select folders to scan
- **Preview Mode**: View folder structure before processing
- **Real-time Monitoring**: Track processing progress
- **Execution History**: View all past scan operations

### Key Features

#### 1. Folder Preview
- **File Structure**: View the complete folder structure
- **File Statistics**: See total files, supported formats, and sizes
- **Validation**: Check folder accessibility before processing
- **Expandable Tree**: Navigate through subdirectories

#### 2. Processing Options
- **Processing Mode**: Choose between queue-based or synchronous processing
- **Concurrency**: Set the number of concurrent processing tasks
- **Recursive Scanning**: Enable/disable subdirectory scanning
- **Depth Control**: Limit the maximum scanning depth
- **Report Generation**: Save processing reports

#### 3. Real-time Monitoring
- **Progress Tracking**: Live updates on file processing
- **Status Updates**: Real-time execution status
- **Error Reporting**: Detailed error messages and recovery
- **Log Streaming**: Live log output from scan operations

### Usage

#### From Dashboard
1. Navigate to **Scan Folder** page
2. Enter folder path or use folder browser
3. Configure processing options
4. Preview folder structure (optional)
5. Start processing
6. Monitor progress in real-time

#### From Command Line
```bash
# Basic scan
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder --queue

# With options
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder \
  --queue --max-depth 3 --concurrent 10 --save-report report.json
```

### Recent Improvements

#### File Path Handling (Latest Update)
- **Fixed f-string formatting** in processing pipeline for proper variable interpolation
- **Enhanced path conversion** between host and container paths
- **Improved original file path tracking** for better data source management
- **Added environment variable support** for host path mapping

#### Error Resolution
- **Resolved "File not found" errors** in processing pipeline
- **Fixed container path conversion** issues
- **Improved error handling** for external folder access
- **Enhanced logging** for better debugging

### Supported File Types
- **Documents**: PDF, DOCX, DOC, TXT, HTML, HTM
- **Images**: PNG, JPG, JPEG, GIF, BMP, TIFF
- **Spreadsheets**: CSV, XLSX, XLS

### Best Practices
1. **Use absolute paths** for folder selection
2. **Preview folders** before processing large directories
3. **Monitor system resources** during concurrent processing
4. **Check execution logs** for detailed progress information
5. **Use dry-run mode** for testing folder accessibility

## 🔧 Configuration

### Environment Variables
```bash
# Service URLs
CORE_PROCESSOR_URL=http://core-processor:8001
FILE_WATCHER_URL=http://file-watcher:8009
STORAGE_MANAGER_URL=http://storage-manager:8004
ELASTICSEARCH_URL=http://elasticsearch:9200
QDRANT_URL=http://qdrant:6333
NEO4J_URL=http://neo4j:7474

# Scan Folder Configuration
HOST_SCAN_FOLDER_PATH=/path/to/host/folder  # For container path mapping
```

### Docker Configuration
The dashboard is configured to work with the MDIS Docker network:
- Uses service names for internal communication
- Mounts logs directory for debugging
- Includes health checks for monitoring

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```
Returns the health status of all monitored services.

### Statistics
```bash
GET /api/stats
```
Returns comprehensive system statistics.

### Documents
```bash
GET /api/documents
```
Returns a list of all documents with their processing status.

### Document Details
```bash
GET /api/documents/{document_id}
```
Returns detailed information about a specific document.

### Services
```bash
GET /api/services
```
Returns detailed information about all services.

### Scan Folder APIs
```bash
# Start scan folder execution
POST /api/scan-folder/start

# Get scan folder executions
GET /api/scan-folder/executions

# Get execution details
GET /api/scan-folder/executions/{execution_id}

# Get execution logs
GET /api/scan-folder/executions/{execution_id}/logs

# Stop execution
POST /api/scan-folder/executions/{execution_id}/stop

# Preview folder structure
POST /api/scan-folder/preview
```

## 🎨 Customization

### Styling
The dashboard uses Bootstrap 5 and custom CSS. You can modify:
- `static/css/dashboard.css` - Custom styles
- `templates/dashboard.html` - HTML structure
- `templates/scan_folder.html` - Scan folder interface

### JavaScript
The dashboard uses vanilla JavaScript for:
- Real-time updates (30-second intervals)
- Interactive features
- Error handling
- Data formatting
- Scan folder management

## 🔍 Troubleshooting

### Common Issues

1. **Services Not Responding**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # Check service logs
   docker-compose logs dashboard
   ```

2. **Connection Errors**
   - Verify all services are running
   - Check network connectivity
   - Ensure correct service URLs

3. **No Data Displayed**
   - Check if documents exist in the system
   - Verify Elasticsearch is running
   - Check service health endpoints

4. **Scan Folder Errors**
   - Verify folder path is absolute and accessible
   - Check folder permissions
   - Ensure Docker is running for container-based scanning
   - Review execution logs for detailed error information

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py
```

## 📈 Performance

### Auto-refresh
- Dashboard refreshes every 30 seconds
- Manual refresh available via button
- Real-time clock updates every second

### Caching
- Service health checks are cached for 5 seconds
- Document data is fetched fresh on each refresh
- Error handling prevents cascading failures

### Scan Folder Performance
- Concurrent processing for improved throughput
- Real-time progress updates
- Efficient file system traversal
- Memory-optimized processing

## 🔒 Security

### Access Control
- No authentication required (development mode)
- Can be extended with authentication middleware
- CORS enabled for cross-origin requests

### Network Security
- Runs on internal Docker network
- Exposes only necessary endpoints
- Health checks for monitoring

### File System Security
- Read-only folder mounting in containers
- Path validation and sanitization
- Permission checking before processing

## 🚀 Deployment

### Production Considerations
1. Add authentication/authorization
2. Configure HTTPS
3. Set up monitoring and alerting
4. Implement rate limiting
5. Add logging and metrics
6. Configure secure file system access

### Scaling
- Stateless design allows horizontal scaling
- Can be deployed behind a load balancer
- Supports multiple instances

## 📚 Integration

### With Existing Services
The dashboard integrates with:
- Core Processor (document management)
- File Watcher (file monitoring)
- Storage Manager (data storage)
- All processing services (health monitoring)
- Elasticsearch (search analytics)
- Qdrant (vector storage)
- Neo4j (graph database)

### External Monitoring
Can be integrated with:
- Prometheus (metrics)
- Grafana (visualization)
- AlertManager (alerts)
- ELK Stack (logging)

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include proper documentation
4. Test with different service states
5. Maintain responsive design

## 📄 License

This dashboard is part of the MDIS system. See the main project license for details. 