# Quick Reference Guide

This guide provides essential information for working with the MEP AI NABOX system.

## 🚀 Quick Start Commands

### Option 1: Admin Mode (Recommended)
```bash
# Start admin mode with web interface
cd mep_ainabox
./start_admin.sh

# Access dashboard and admin panel
# Dashboard: http://localhost:8010
# Admin Panel: http://localhost:8010/admin
```

### Option 2: Traditional Startup
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
curl http://localhost:8009/health

# View logs
docker-compose logs -f
```

### Test the System
```bash
# Run simple test
python test_simple_upload.py

# Run comprehensive test
python test_system.py

# Test file watcher
python test_file_watcher.py
```

## 📊 Service Ports

| Service | Port | Description |
|---------|------|-------------|
| **Dashboard** | **8010** | **Web monitoring interface** |
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

## 📁 File Monitoring

### File Watcher Commands
```bash
# Check file watcher status
curl http://localhost:8009/api/v1/watch/status

# List processed files
curl http://localhost:8009/api/v1/watch/processed

# Add file to watch folder
echo "Test content" > core/watch_folder/test_file.txt
```

### File Upload Monitoring Script
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

# Update job status
POST /documents/{document_id}/job-status
{
  "status": "completed",
  "message": "Processing finished"
}
```

### File Watcher (8009)
```bash
# Health check
GET /health

# Get status
GET /api/v1/watch/status

# List processed files
GET /api/v1/watch/processed

# Manually process file
POST /api/v1/watch/process
{
  "file_path": "/app/watch_folder/test.txt"
}
```

### Dashboard (8010)
```bash
# Main dashboard
GET /

# Admin panel
GET /admin

# System health
GET /api/health

# Service status
GET /api/services

# Admin status
GET /api/admin/status

# Start all services
POST /api/admin/start-services

# Get startup logs
GET /api/admin/startup-logs

# Service details
GET /service/{service_name}

# Service logs
GET /api/service/{service_name}/logs

# Service metrics
GET /api/service/{service_name}/metrics
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

#### File Watcher Issues
```bash
# Check file watcher status
curl http://localhost:8009/api/v1/watch/status

# Check file watcher logs
docker-compose logs -f file-watcher

# Verify watch folder permissions
ls -la core/watch_folder/

# Restart file watcher if needed
docker-compose restart file-watcher
```

#### Dashboard Issues
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

#### Duplicate File Errors
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

# View specific service
docker-compose logs -f core-processor

# Search for errors
docker-compose logs | grep ERROR

# Search for UUID errors
docker-compose logs | grep "inconsistent types"

# Search for file watcher activity
docker-compose logs | grep "file_watcher"
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
│   ├── file_watcher/         # File monitoring service
│   ├── documents/            # Document storage
│   ├── processed/            # Processed files
│   ├── temp/                 # Temporary files
│   ├── logs/                 # Application logs
│   ├── watch_folder/         # File watch directory
│   ├── test_*.py             # Test scripts
│   └── demo_*.py             # Demo scripts
├── check_uploaded_files.sh   # File upload monitoring script
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

# File watcher
WATCH_FOLDER_PATH=./watch_folder
```

## 🆘 Emergency Commands

### Restart All Services
```bash
# Stop all services
docker-compose down

# Start infrastructure
cd services && docker-compose up -d

# Start core system
cd ../core && ./start.sh
```

### Reset File Watcher
```bash
# Restart file watcher
docker-compose restart file-watcher

# Check status
curl http://localhost:8009/api/v1/watch/status
```

### Clear Failed Documents
```bash
# Check failed documents
./check_uploaded_files.sh failed

# Reprocess specific document
curl -X POST http://localhost:8001/documents/{document_id}/reprocess
```

## 📊 Monitoring Commands

### System Status
```bash
# Check all service health
for port in 8000 8001 8002 8003 8004 8009; do
  echo "Port $port: $(curl -s http://localhost:$port/health | jq -r '.status // .message // "Unknown"')"
done
```

### File Processing Status
```bash
# Get processing summary
./check_uploaded_files.sh status

# Get recent activity
./check_uploaded_files.sh recent

# Get file watcher status
./check_uploaded_files.sh watcher
```

### Resource Usage
```bash
# Check container resource usage
docker stats --no-stream

# Check disk usage
du -sh core/documents core/processed core/temp
``` 