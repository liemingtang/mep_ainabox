# MEP AI NABOX

A comprehensive AI-powered file scanning and analysis system that allows users to point to any folder on their system, scan all files, and create a rich collection of information for natural language queries and advanced search capabilities.

## 🎯 System Overview

MEP AI NABOX is designed to be a universal file intelligence system that:

- **Scans any folder** on the user's system recursively
- **Processes all file types** including documents, images, videos, and binary files
- **Generates rich metadata** using custom AI analysis for each file
- **Enables natural language queries** across the entire scanned dataset
- **Supports extensible data sources** (files, databases, emails, etc.)
- **Provides photo understanding** through custom vision analysis
- **Self-contained architecture** with no dependencies on other MEP projects
- **Real-time file monitoring** with automatic processing of new files
- **Duplicate file handling** with intelligent deduplication

## 🏗️ Current Architecture

### Core System (Implemented)

The system currently implements a **Modular Document Intelligence System (MDIS)** with the following working components:

#### 1. **Core Services** ✅
- **API Gateway** (Port 8000): Unified entry point for all client interactions
- **Core Processor** (Port 8001): Main document processing orchestrator
- **Document Router** (Port 8002): Intelligent document routing and analysis
- **Processing Pipeline** (Port 8003): Orchestrated document processing workflow
- **Storage Manager** (Port 8004): Unified data storage and retrieval interface

#### 2. **Processing Services** ✅
- **Text Processor** (Port 8005): Text extraction and cleaning
- **Metadata Processor** (Port 8006): Metadata extraction and validation
- **Embedding Processor** (Port 8007): Vector embedding generation
- **Entity Processor** (Port 8008): Entity extraction and relationship mapping

#### 3. **Support Services** ✅
- **File Watcher** (Port 8009): Monitor local folders for new documents
  - Real-time file monitoring using watchdog library
  - Automatic file detection and upload to core processor
  - File validation and metadata creation
  - Asynchronous processing with error handling
  - API endpoints for status monitoring and manual processing

#### 4. **Infrastructure Services** ✅
- **PostgreSQL**: Document metadata and relationships
- **Elasticsearch**: Full-text search and content indexing
- **Qdrant**: Vector embeddings for semantic search
- **Neo4j**: Graph relationships and entity mapping
- **MinIO**: Object storage for files
- **Redis**: Caching and session management

#### 5. **Dashboard System** ✅
- **Web Dashboard** (Port 8010): Real-time monitoring and management interface
- **Admin Panel**: Web-based service management with one-click startup
- **Host-based Architecture**: Runs directly on host for better performance and access
- **Real-time Monitoring**: Live service status, logs, and metrics
- **Service Management**: Start, stop, and monitor all services through web interface

### Data Storage Architecture

The system uses multiple specialized databases optimized for different use cases:

- **PostgreSQL**: Primary metadata storage with UUID support and JSON serialization
- **Elasticsearch**: Full-text search with advanced indexing
- **Qdrant**: High-performance vector similarity search
- **Neo4j**: Graph database for relationship mapping and reasoning
- **MinIO**: Object storage for file management
- **Redis**: Caching and session management

## 🚀 Quick Start

### Option 1: Admin Mode (Recommended)
The easiest way to get started is using the Admin Mode, which provides a web-based interface to manage all services:

```bash
cd mep_ainabox
./start_admin.sh
```

This will:
- Start the dashboard on http://localhost:8010
- Provide an admin panel at http://localhost:8010/admin
- Allow you to start all services with one click

**To stop all services:**
```bash
cd mep_ainabox
./stop_admin.sh
```

This will:
- Stop the dashboard service
- Stop all core system services
- Stop all infrastructure services
- Clean up all Python processes
- Remove all Docker containers
- Provide a complete system shutdown

### Option 2: Traditional Startup

#### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM available for all services
- Python 3.11+ (for local development)

#### 1. Start Infrastructure Services
```bash
cd mep_ainabox/services
docker-compose up -d
```

#### 2. Start Core System
```bash
cd mep_ainabox/core
cp env.example .env
# Edit .env file with your configuration

# Make startup script executable
chmod +x start.sh

# Start the core system
./start.sh
```

#### 3. Verify Installation
```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# View logs
docker-compose logs -f
```

#### 4. Test Document Upload
```bash
# Run the test script
python test_simple_upload.py
```

#### 5. Test File Watcher (Optional)
```bash
# Add a file to the watch folder
echo "Test content" > watch_folder/test_file.txt

# Check uploaded files
./check_uploaded_files.sh watch
```

## 📁 Current Directory Structure

```
mep_ainabox/
├── README.md                 # This file
├── README_architecture.md    # Detailed architecture documentation
├── TECHNICAL_DETAILS.md      # Technical implementation details
├── QUICK_REFERENCE.md        # Quick reference guide
├── CHANGELOG.md              # Change history
├── check_uploaded_files.sh   # File upload monitoring script
├── services/                 # Infrastructure services
│   ├── docker-compose.yml    # Infrastructure stack
│   ├── config/               # Service configurations
│   └── volumes/              # Persistent data storage
├── core/                     # Core system implementation
│   ├── README.md             # Core system documentation
│   ├── docker-compose.yml    # Core system services
│   ├── env.example           # Environment variables template
│   ├── start.sh              # Startup script
│   ├── start_admin.sh        # Admin mode startup script
│   ├── start_dashboard_host.sh # Dashboard host startup script
│   ├── stop_dashboard_host.sh # Dashboard host stop script
│   ├── core_processor/       # Core processing orchestrator
│   ├── document_router/      # Document routing service
│   ├── processing_pipeline/  # Processing workflow service
│   ├── storage_manager/      # Storage management service
│   ├── api_gateway/          # API gateway service
│   ├── dashboard/            # Web dashboard system
│   │   ├── main.py           # Dashboard FastAPI application
│   │   ├── requirements.txt  # Dashboard dependencies
│   │   ├── templates/        # HTML templates
│   │   │   ├── dashboard.html # Main dashboard page
│   │   │   ├── admin.html    # Admin panel page
│   │   │   └── service_detail.html # Service detail page
│   │   └── static/           # Static assets (CSS, JS)
│   ├── processors/           # Document processors
│   │   ├── text_processor/   # Text extraction
│   │   ├── metadata_processor/ # Metadata extraction
│   │   ├── embedding_processor/ # Embedding generation
│   │   └── entity_processor/ # Entity extraction
│   ├── file_watcher/         # File monitoring service
│   ├── documents/            # Local document storage
│   ├── processed/            # Processed document storage
│   ├── temp/                 # Temporary processing files
│   ├── logs/                 # Application logs
│   ├── watch_folder/         # File watch directory
│   ├── test_system.py        # Comprehensive system test
│   ├── test_simple_upload.py # Simple upload test
│   ├── test_upload_only.py   # Upload-only test
│   ├── test_file_watcher.py  # File watcher test
│   └── demo_file_watcher.py  # File watcher demo
└── requirements.txt          # Python dependencies
```

## 🔧 Configuration

### Environment Variables
The system uses environment variables for configuration. Key variables include:

```bash
# System Configuration
SYSTEM_ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Local File Paths
LOCAL_DOCUMENTS_PATH=./documents
PROCESSED_DOCUMENTS_PATH=./processed
TEMP_PROCESSING_PATH=./temp
WATCH_FOLDER_PATH=./watch_folder

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mep_ainabox
POSTGRES_USER=mep_user
POSTGRES_PASSWORD=mep_password

# External API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
HUGGINGFACE_API_TOKEN=your-huggingface-api-token
```

## 📊 API Endpoints

### Core Processor (Port 8001)
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /documents/upload` - Upload and process document
- `GET /documents/{id}` - Get document information
- `GET /documents/{id}/processing-status` - Get processing status
- `POST /documents/{id}/reprocess` - Reprocess document
- `GET /documents` - List documents with filtering
- `DELETE /documents/{id}` - Delete document
- `GET /stats` - System statistics
- `POST /documents/{id}/job-status` - Update job status

### File Watcher (Port 8009)
- `GET /health` - Health check
- `GET /api/v1/watch/status` - File watcher status
- `GET /api/v1/watch/processed` - List processed files
- `POST /api/v1/watch/process` - Manually process a file

### API Gateway (Port 8000)
- `GET /health` - Health check
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document
- `POST /api/v1/search/text` - Full-text search
- `POST /api/v1/search/semantic` - Semantic search

### Dashboard (Port 8010)
- `GET /` - Main dashboard page
- `GET /admin` - Admin panel page
- `GET /api/health` - System health status
- `GET /api/stats` - System statistics
- `GET /api/services` - Service status overview
- `GET /api/admin/status` - Admin panel status
- `POST /api/admin/start-services` - Start all services
- `GET /api/admin/startup-logs` - Real-time startup logs
- `GET /service/{service_name}` - Individual service details
- `GET /api/service/{service_name}/logs` - Service logs
- `GET /api/service/{service_name}/metrics` - Service metrics
- `GET /api/service/{service_name}/configuration` - Service configuration

## 🔄 Processing Workflow

1. **Document Upload**: Document is uploaded via API Gateway or File Watcher
2. **Duplicate Detection**: System checks for existing files by hash
3. **Document Routing**: Document Router analyzes content and determines processing steps
4. **Processing Pipeline**: Orchestrated workflow through multiple processors:
   - Text extraction
   - Metadata extraction
   - Embedding generation
   - Entity extraction
   - Relationship mapping
5. **Domain Analysis**: Specialized analysis (climate, financial, legal)
6. **Storage**: Results stored across multiple databases
7. **Search Indexing**: Content indexed for search and retrieval

## 📁 File Monitoring

### File Watcher Service
The file watcher service monitors the `watch_folder` directory for new files and automatically processes them:

```bash
# Check file watcher status
curl http://localhost:8009/api/v1/watch/status

# Add a file to the watch folder
echo "Test content" > core/watch_folder/test_file.txt
```

### File Upload Monitoring
Use the provided script to monitor uploaded files:

```bash
# Show all uploaded files
./check_uploaded_files.sh all

# Show only watch folder files
./check_uploaded_files.sh watch

# Show processing status summary
./check_uploaded_files.sh status

# Show recent uploads
./check_uploaded_files.sh recent

# Show failed uploads
./check_uploaded_files.sh failed

# Show file watcher status
./check_uploaded_files.sh watcher

# Show file counts
./check_uploaded_files.sh count
```

## 🗄️ Data Storage

The system uses multiple specialized databases:

- **PostgreSQL**: Document metadata and relationships
- **Elasticsearch**: Full-text search and content indexing
- **Qdrant**: Vector embeddings for semantic search
- **Neo4j**: Graph relationships and entity mapping
- **MinIO**: Object storage for files
- **Redis**: Caching and session management

## 📈 Monitoring and Observability

### Web Dashboard
The system includes a comprehensive web dashboard for monitoring and management:

- **Main Dashboard**: http://localhost:8010 - Real-time system overview
- **Admin Panel**: http://localhost:8010/admin - Service management interface
- **Service Details**: Individual service monitoring and configuration
- **Real-time Logs**: Live log streaming and monitoring
- **Health Monitoring**: Automatic health checks and status updates

### Health Checks
All services provide health check endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
# ... etc
```

### Metrics
Prometheus metrics are available at `/metrics` endpoints:
```bash
curl http://localhost:8000/metrics
```

### Logging
Structured JSON logging is used throughout the system. Logs are available:
- **Dashboard Logs**: `core/logs/dashboard.log`
- **Service Logs**: Individual service logs in respective directories
- **Container Logs**: `docker-compose logs -f`
- **Startup Logs**: Real-time startup progress tracking

## 🔒 Security

### Authentication
- JWT-based authentication
- Configurable token expiry
- Role-based access control

### Data Protection
- Data encryption at rest
- Transport layer security (TLS)
- Audit logging for all operations

### Network Security
- Service-to-service communication over internal Docker network
- API Gateway as single entry point
- Rate limiting and request validation

## 🧪 Testing

### System Tests
```bash
# Run comprehensive system test
python test_system.py

# Run simple upload test
python test_simple_upload.py

# Run upload-only test
python test_upload_only.py

# Run file watcher test
python test_file_watcher.py

# Run file watcher demo
python demo_file_watcher.py
```

### API Tests
```bash
# Test document upload
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "file_path": "/app/documents/test.pdf"}'

# Test file watcher status
curl http://localhost:8009/api/v1/watch/status
```

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check if infrastructure services are running
   docker ps | grep mep-
   
   # Check logs
   docker-compose logs -f
   ```

2. **Database connection issues**
   ```bash
   # Check database health
   curl http://localhost:5432/health
   
   # Verify network connectivity
   docker network ls | grep mep-services-network
   ```

3. **File permission issues**
   ```bash
   # Fix permissions
   chmod -R 755 documents processed temp logs watch_folder
   ```

4. **Memory issues**
   ```bash
   # Check resource usage
   docker stats
   
   # Increase Docker memory limit if needed
   ```

5. **File watcher not detecting files**
   ```bash
   # Check file watcher status
   curl http://localhost:8009/api/v1/watch/status
   
   # Check file watcher logs
   docker-compose logs -f file-watcher
   
   # Verify watch folder permissions
   ls -la watch_folder/
   ```

6. **Dashboard issues**
   ```bash
   # Check if dashboard is running
   curl http://localhost:8010/api/health
   
   # Check dashboard logs
   tail -f core/logs/dashboard.log
   
   # Restart dashboard
   cd core && ./stop_dashboard_host.sh && ./start_dashboard_host.sh --background
   
   # Check if port 8010 is available
   netstat -tulpn | grep 8010
   ```

7. **Duplicate file errors**
   ```bash
   # Check for duplicate files
   ./check_uploaded_files.sh failed
   
   # The system now handles duplicates automatically
   # Check the changelog for recent fixes
   ```

### Log Analysis
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f core-processor

# Search logs for errors
docker-compose logs | grep ERROR
```

## 🔄 Development

### Adding New Processors
1. Create new processor directory in `processors/`
2. Implement processor service with FastAPI
3. Add to `docker-compose.yml`
4. Update processing pipeline configuration
5. Add to processing workflow

### Adding New Storage Backends
1. Update `storage_manager/` service
2. Add configuration in `config/main.yaml`
3. Update database initialization
4. Add health checks

### Configuration Changes
1. Update `config/main.yaml`
2. Restart affected services: `docker-compose restart <service>`
3. Verify configuration: `curl http://localhost:8000/health`

## 📚 Documentation

- [Architecture Document](README_architecture.md)
- [Technical Details](TECHNICAL_DETAILS.md)
- [Quick Reference](QUICK_REFERENCE.md)
- [Changelog](CHANGELOG.md)
- [Admin Startup Guide](ADMIN_STARTUP_GUIDE.md) - Web-based service management
- [Core System Documentation](core/README.md)
- [API Documentation](core/api_documentation.md)
- [Deployment Guide](core/deployment_guide.md)
- [Development Guide](core/development_guide.md)

## 🤝 Contributing

1. Follow the established architecture patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Use structured logging and metrics
5. Follow security best practices

## 📄 License

This project is part of the MEP AI NABOX system. See the main project license for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs and metrics
3. Check the architecture documentation
4. Create an issue with detailed information    
