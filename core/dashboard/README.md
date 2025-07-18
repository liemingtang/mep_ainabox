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

## 🎨 Customization

### Styling
The dashboard uses Bootstrap 5 and custom CSS. You can modify:
- `static/css/dashboard.css` - Custom styles
- `templates/dashboard.html` - HTML structure

### JavaScript
The dashboard uses vanilla JavaScript for:
- Real-time updates (30-second intervals)
- Interactive features
- Error handling
- Data formatting

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

## 🔒 Security

### Access Control
- No authentication required (development mode)
- Can be extended with authentication middleware
- CORS enabled for cross-origin requests

### Network Security
- Runs on internal Docker network
- Exposes only necessary endpoints
- Health checks for monitoring

## 🚀 Deployment

### Production Considerations
1. Add authentication/authorization
2. Configure HTTPS
3. Set up monitoring and alerting
4. Implement rate limiting
5. Add logging and metrics

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