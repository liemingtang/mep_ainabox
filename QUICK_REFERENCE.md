# Quick Reference Guide

This guide provides essential information for working with the MEP AI NABOX system.

## 🚀 Quick Start Commands

### Start the System
```bash
# Start infrastructure services
cd mep_ainabox/services
docker-compose up -d

# Start core system
cd ../core
cp env.example .env
chmod +x start.sh
./start.sh
```

### Check System Health
```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health

# View logs
docker-compose logs -f
```

### Test the System
```bash
# Run simple test
python test_simple_upload.py

# Run comprehensive test
python test_system.py
```

## 📊 Service Ports

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Main entry point |
| Core Processor | 8001 | Document processing |
| Document Router | 8002 | Document routing |
| Processing Pipeline | 8003 | Workflow orchestration |
| Storage Manager | 8004 | Data storage |
| Text Processor | 8005 | Text extraction |
| Metadata Processor | 8006 | Metadata extraction |
| Embedding Processor | 8007 | Vector embeddings |
| Entity Processor | 8008 | Entity extraction |
| File Watcher | 8009 | File monitoring |

## 🗄️ Database Connections

| Service | Host | Port | Database |
|---------|------|------|----------|
| PostgreSQL | postgres | 5432 | mep_ainabox |
| Elasticsearch | elasticsearch | 9200 | - |
| Qdrant | qdrant | 6333 | - |
| Neo4j | neo4j | 7474 | - |
| Redis | redis | 6379 | - |
| MinIO | minio | 9000 | - |

## 🔧 Key API Endpoints

### Core Processor (8001)
```bash
# Health check
GET /health

# Upload document
POST /documents/upload
{
  "filename": "document.pdf",
  "file_path": "/app/documents/document.pdf",
  "file_type": "pdf",
  "file_size": 1024,
  "metadata": {"source": "test"}
}

# Get document
GET /documents/{document_id}

# List documents
GET /documents?status=processed&limit=10

# Get processing status
GET /documents/{document_id}/processing-status
```

### API Gateway (8000)
```bash
# Health check
GET /health

# Upload document
POST /api/v1/documents
{
  "filename": "document.pdf",
  "file_path": "/app/documents/document.pdf"
}

# Search documents
POST /api/v1/search/text
{
  "query": "climate change",
  "limit": 10
}
```

## 🔍 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check if infrastructure is running
docker ps | grep mep-

# Check logs
docker-compose logs -f core-processor
```

#### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U mep_user

# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check Qdrant
curl http://localhost:6333/collections
```

#### UUID Type Errors
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

# View specific service
docker-compose logs -f core-processor

# Search for errors
docker-compose logs | grep ERROR

# Search for UUID errors
docker-compose logs | grep "inconsistent types"
```

## 📁 File Structure

```
mep_ainabox/
├── services/                 # Infrastructure
│   ├── docker-compose.yml    # Infrastructure stack
│   └── config/               # Service configs
├── core/                     # Core system
│   ├── docker-compose.yml    # Core services
│   ├── start.sh              # Startup script
│   ├── env.example           # Environment template
│   ├── core_processor/       # Main processor
│   ├── processors/           # Document processors
│   ├── documents/            # Document storage
│   ├── processed/            # Processed files
│   ├── temp/                 # Temporary files
│   ├── logs/                 # Application logs
│   └── test_*.py             # Test scripts
└── README.md                 # Main documentation
```

## 🔧 Configuration

### Environment Variables
```bash
# Required for operation
POSTGRES_HOST=postgres
POSTGRES_DB=mep_ainabox
POSTGRES_USER=mep_user
POSTGRES_PASSWORD=mep_password

# External services
ELASTICSEARCH_HOST=elasticsearch
QDRANT_HOST=qdrant
QDRANT_API_KEY=your-api-key

# API keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
HUGGINGFACE_API_TOKEN=your-huggingface-token
```

### Database Schema
```sql
-- Key tables
documents              # Document metadata
processing_jobs        # Processing status
document_content       # Extracted content
document_embeddings    # Vector embeddings
document_entities      # Extracted entities
document_relationships # Document relationships
```

## 🧪 Testing

### Test Scripts
```bash
# Simple upload test
python test_simple_upload.py

# Comprehensive system test
python test_system.py

# Upload-only test
python test_upload_only.py
```

### Manual Testing
```bash
# Test document upload
curl -X POST http://localhost:8001/documents/upload \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "file_path": "/app/documents/test.pdf",
    "file_type": "pdf",
    "file_size": 1024,
    "metadata": {"source": "test"}
  }'

# Test health check
curl http://localhost:8001/health
```

## 📈 Monitoring

### Health Checks
```bash
# All services
for port in 8000 8001 8002 8003 8004; do
  echo "Port $port: $(curl -s http://localhost:$port/health | jq -r '.status')"
done
```

### Metrics
```bash
# Prometheus metrics
curl http://localhost:8001/metrics
```

### Resource Usage
```bash
# Docker stats
docker stats

# Container logs
docker-compose logs -f
```

## 🔒 Security

### API Keys
- Qdrant API key required for vector database
- OpenAI/Anthropic keys for AI processing
- HuggingFace token for model access

### Network Security
- Services communicate over internal Docker network
- Only API Gateway exposed externally
- All internal communication isolated

## 🚨 Emergency Procedures

### System Reset
```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Database Reset
```bash
# Backup first
docker-compose exec postgres pg_dump -U mep_user mep_ainabox > backup.sql

# Reset database
docker-compose exec postgres psql -U mep_user -d mep_ainabox -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Log Cleanup
```bash
# Clear logs
docker-compose logs --tail=0
rm -rf logs/*
```

## 📞 Support

### Documentation
- [Main README](README.md)
- [Architecture](README_architecture.md)
- [Technical Details](TECHNICAL_DETAILS.md)
- [Changelog](CHANGELOG.md)

### Debugging
1. Check service health: `curl http://localhost:8001/health`
2. Review logs: `docker-compose logs -f`
3. Check database: `docker-compose exec postgres psql -U mep_user -d mep_ainabox`
4. Verify network: `docker network ls`

### Common Commands
```bash
# Restart specific service
docker-compose restart core-processor

# View service logs
docker-compose logs -f core-processor

# Execute in container
docker-compose exec core-processor bash

# Check resource usage
docker stats

# Update environment
docker-compose down
# Edit .env file
docker-compose up -d
``` 