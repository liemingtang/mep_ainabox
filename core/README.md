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

# View logs
docker-compose logs -f
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
├── document_router/         # Document routing service
├── processing_pipeline/     # Processing workflow service
├── storage_manager/         # Storage management service
├── api_gateway/            # API gateway service
├── processors/             # Document processors
│   ├── text_processor/     # Text extraction
│   ├── metadata_processor/ # Metadata extraction
│   ├── embedding_processor/ # Embedding generation
│   └── entity_processor/   # Entity extraction
├── file_watcher/           # File monitoring service
├── documents/              # Local document storage
├── processed/              # Processed document storage
├── temp/                   # Temporary processing files
├── logs/                   # Application logs
└── watch_folder/           # File watch directory
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

## 🗄️ Data Storage

The system uses multiple specialized databases:

- **PostgreSQL**: Document metadata and relationships
- **Elasticsearch**: Full-text search and content indexing
- **Qdrant**: Vector embeddings for semantic search
- **Neo4j**: Graph relationships and entity mapping
- **MinIO**: Object storage for files
- **Redis**: Caching and session management

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

## 📄 License

This project is part of the MEP AI NABOX system. See the main project license for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs and metrics
3. Check the architecture documentation
4. Create an issue with detailed information 