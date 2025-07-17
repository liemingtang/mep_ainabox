# Core System - Modular Document Intelligence System (MDIS)

This directory contains the core components of the Modular Document Intelligence System as described in the architecture document. The system is designed to process, analyze, and extract insights from large volumes of structured and unstructured documents.

## 🏗️ Architecture Overview

The core system follows a modular microservices architecture with the following components:

### Core Services
- **API Gateway** (Port 8000): Unified entry point for all client interactions
- **Core Processor** (Port 8001): Main document processing orchestrator
- **Document Router** (Port 8002): Intelligent document routing and analysis
- **Processing Pipeline** (Port 8003): Orchestrated document processing workflow
- **Storage Manager** (Port 8004): Unified data storage and retrieval interface

### Processing Services
- **Text Processor** (Port 8005): Text extraction and cleaning
- **Metadata Processor** (Port 8006): Metadata extraction and validation
- **Embedding Processor** (Port 8007): Vector embedding generation
- **Entity Processor** (Port 8008): Entity extraction and relationship mapping

### Support Services
- **File Watcher** (Port 8009): Monitor local folders for new documents

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Infrastructure services running (PostgreSQL, Elasticsearch, Qdrant, Neo4j, Redis, MinIO)
- At least 4GB RAM available for all services

### 1. Start Infrastructure Services
```bash
cd ../services
docker-compose up -d
```

### 2. Configure Environment
```bash
cd ../core
cp env.example .env
# Edit .env file with your configuration
```

### 3. Start Core System
```bash
# Make startup script executable
chmod +x start.sh

# Start the core system
./start.sh
```

### 4. Verify Installation
```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health

# View logs
docker-compose logs -f
```

### 5. Test Document Upload
```bash
# Run the simple test script
python test_simple_upload.py

# Or run comprehensive system test
python test_system.py
```

## 📁 Directory Structure

```
core/
├── README.md                 # This file
├── docker-compose.yml        # Core system services
├── env.example              # Environment variables template
├── start.sh                 # Startup script
├── config/
│   └── main.yaml            # Main configuration file
├── core_processor/          # Core processing orchestrator
│   ├── main.py              # FastAPI application
│   ├── app/
│   │   ├── api/             # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── models/          # Data models
│   │   └── database/        # Database connections
│   ├── Dockerfile           # Container definition
│   └── requirements.txt     # Python dependencies
├── document_router/         # Document routing service
├── processing_pipeline/     # Processing workflow service
├── storage_manager/         # Storage management service
├── api_gateway/            # API gateway service
├── processors/             # Document processors
│   ├── text_processor/     # Text extraction
│   ├── metadata_processor/ # Metadata extraction
│   ├── embedding_processor/ # Embedding generation
│   └── entity_processor/   # Entity extraction
├── file_watcher/           # File monitoring service (fully functional)
├── documents/              # Local document storage
├── processed/              # Processed document storage
├── temp/                   # Temporary processing files
├── logs/                   # Application logs
├── watch_folder/           # File watch directory
├── test_system.py          # Comprehensive system test
├── test_simple_upload.py   # Simple upload test
└── test_upload_only.py     # Upload-only test
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

### Configuration File
The main configuration is in `config/main.yaml` and includes:

- Processing settings (file size limits, supported formats)
- Storage configuration for all databases
- Module settings (climate, financial, legal analysis)
- Processing pipeline configuration
- Routing rules for document classification
- Security and monitoring settings

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

### Text Processor (Port 8005)
- `GET /health` - Health check
- `POST /extract-text` - Extract text from document
- `POST /process` - Process document from pipeline

### API Gateway (Port 8000)
- `GET /health` - Health check
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document
- `POST /api/v1/search/text` - Full-text search
- `POST /api/v1/search/semantic` - Semantic search

### File Watcher (Port 8009)
- `GET /health` - Health check
- `GET /` - Service information and status
- `POST /api/v1/watch/start` - Start file watching
- `POST /api/v1/watch/stop` - Stop file watching
- `GET /api/v1/watch/status` - Get watcher status
- `GET /api/v1/watch/processed` - List processed files
- `GET /api/v1/watch/errors` - List error files
- `POST /api/v1/watch/clear-history` - Clear processing history
- `POST /api/v1/watch/process-file` - Manually process a specific file

## 🔄 Processing Workflow

1. **Document Upload**: Document is uploaded via API Gateway
2. **Document Routing**: Document Router analyzes content and determines processing steps
3. **Processing Pipeline**: Orchestrated workflow through multiple processors:
   - Text extraction
   - Metadata extraction
   - Embedding generation
   - Entity extraction
   - Relationship mapping
4. **Domain Analysis**: Specialized analysis (climate, financial, legal)
5. **Storage**: Results stored across multiple databases
6. **Search Indexing**: Content indexed for search and retrieval

## 📁 File Watcher Functionality

The File Watcher service provides automatic document processing by monitoring designated folders for new files.

### Features
- **Automatic Detection**: Monitors the `watch_folder` for new files
- **File Validation**: Validates file types and sizes before processing
- **Supported Formats**: PDF, DOCX, TXT, HTML, Images (PNG, JPG, etc.), CSV, Excel files
- **Automatic Processing**: Sends valid files to the Core Processor for full processing
- **File Organization**: Moves processed files to `processed/` folder and errors to `error/` folder
- **Status Monitoring**: Real-time status tracking and processing history
- **Manual Processing**: API endpoint for manually processing specific files

### Usage

#### Automatic Processing
1. Start the file watcher:
   ```bash
   curl -X POST http://localhost:8009/api/v1/watch/start
   ```

2. Place files in the watch folder:
   ```bash
   cp document.pdf ./watch_folder/
   ```

3. Monitor processing status:
   ```bash
   curl http://localhost:8009/api/v1/watch/status
   ```

#### Manual Processing
```bash
# Process a specific file
curl -X POST "http://localhost:8009/api/v1/watch/process-file?file_path=/path/to/file.pdf"
```

#### Monitoring
```bash
# Check processed files
curl http://localhost:8009/api/v1/watch/processed

# Check error files
curl http://localhost:8009/api/v1/watch/errors

# Clear history
curl -X POST http://localhost:8009/api/v1/watch/clear-history
```

### File Processing Flow
1. **File Detection**: File watcher detects new files in `watch_folder`
2. **Validation**: Checks file extension and size (max 100MB)
3. **Metadata Creation**: Generates file hash and metadata
4. **Processing**: Sends to Core Processor via API
5. **File Movement**: Moves file to appropriate folder based on result
6. **Status Update**: Updates processing history and status

### Supported File Types
- **Documents**: `.pdf`, `.docx`, `.doc`
- **Text**: `.txt`, `.html`, `.htm`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **Data**: `.csv`, `.xlsx`, `.xls`

### Testing
```bash
# Run file watcher tests
python test_file_watcher.py

# Run demonstration
python demo_file_watcher.py
```

## 🗄️ Data Storage

The system uses multiple specialized databases:

- **PostgreSQL**: Document metadata and relationships
- **Elasticsearch**: Full-text search and content indexing
- **Qdrant**: Vector embeddings for semantic search
- **Neo4j**: Graph relationships and entity mapping
- **MinIO**: Object storage for files
- **Redis**: Caching and session management

## 🔧 Recent Fixes and Improvements

### UUID Type Handling
- **Fixed**: UUID to string conversion in all SQL queries
- **Fixed**: JSON serialization for metadata fields
- **Fixed**: Database schema initialization with proper UUID support
- **Fixed**: API endpoint parameter handling for UUIDs

### Database Connectivity
- **Fixed**: PostgreSQL connection pool initialization
- **Fixed**: Elasticsearch client configuration
- **Fixed**: Qdrant API key authentication
- **Fixed**: Neo4j driver initialization
- **Fixed**: Redis connection handling
- **Fixed**: MinIO client setup

### Service Health
- **Fixed**: Prometheus metrics registration conflicts
- **Fixed**: Health check endpoints for all services
- **Fixed**: Service startup sequence and dependencies
- **Fixed**: Environment variable loading in startup scripts

### Testing and Validation
- **Added**: Comprehensive system test script (`test_system.py`)
- **Added**: Simple upload test script (`test_simple_upload.py`)
- **Added**: Upload-only test script (`test_upload_only.py`)
- **Added**: Detailed logging and error reporting
- **Added**: Health check validation for all services

## 📈 Monitoring and Observability

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
- In container logs: `docker-compose logs -f`
- In mounted log directories: `./logs/`

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

# Run file watcher tests
python test_file_watcher.py

# Run file watcher demonstration
python demo_file_watcher.py
```

### Unit Tests
```bash
# Run tests for core processor
cd core_processor
python -m pytest tests/

# Run tests for text processor
cd ../processors/text_processor
python -m pytest tests/
```

### Integration Tests
```bash
# Test API endpoints
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "file_path": "/app/documents/test.pdf"}'
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

5. **UUID type mismatch errors**
   ```bash
   # Rebuild containers after UUID fixes
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
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

### Database Schema Changes
1. Update schema files in `core_processor/app/database/`
2. Rebuild containers: `docker-compose build --no-cache`
3. Restart services: `docker-compose up -d`
4. Verify schema initialization in logs

## 📚 Documentation

- [Architecture Document](../README_architecture.md)
- [API Documentation](api_documentation.md)
- [Deployment Guide](deployment_guide.md)
- [Development Guide](development_guide.md)

## 🤝 Contributing

1. Follow the established architecture patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Use structured logging and metrics
5. Follow security best practices
6. Test UUID handling for new database operations
7. Validate service health checks

## 📄 License

This project is part of the MEP AI NABOX system. See the main project license for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs and metrics
3. Check the architecture documentation
4. Create an issue with detailed information 