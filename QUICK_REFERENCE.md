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

### Folder Scanning Script
```bash
# Scan a folder with dry run (recommended first)
./scan_folder.sh /path/to/folder --dry-run

# Scan a folder and process all files
./scan_folder.sh /path/to/folder

# Scan with custom settings
./scan_folder.sh /path/to/folder --concurrent 10 --save-report report.json

# Scan with specific processor URL
./scan_folder.sh /path/to/folder --processor-url http://localhost:8001

# Non-recursive scanning
./scan_folder.sh /path/to/folder --no-recursive

# Scan with maximum depth limit
./scan_folder.sh /path/to/folder --max-depth 3

# Show help
./scan_folder.sh --help
```

### Enhanced Folder Scanning (Latest Update)
```bash
# Basic scan with proper path mapping (recommended)
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder --queue

# Advanced scan with all options
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder \
  --queue --max-depth 3 --concurrent 10 --save-report report.json

# Scan external drive or network folder
docker run --rm --network host \
  -v /media/user/external_drive/documents:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/media/user/external_drive/documents \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder --queue
```

### Scan Folder Dashboard
```bash
# Access scan folder interface
http://localhost:8010/scan-folder

# API endpoints for scan folder management
POST /api/scan-folder/start          # Start new scan execution
GET  /api/scan-folder/executions     # List all executions
POST /api/scan-folder/preview        # Preview folder structure
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

#### Dashboard Error Handling
The dashboard has been enhanced with comprehensive error handling:

**Expected Behavior When Services Are Down**:
- Dashboard loads without error alerts
- Statistics show zero values (0 documents, 0 services)
- Service health shows all services as unavailable
- Documents table shows "No documents found"
- Pipeline status shows services as "unknown" or "error"

**If You See Error Alerts**:
```bash
# Check browser console for warnings (not errors)
# Open Developer Tools (F12) and check Console tab

# Verify dashboard is running
curl http://localhost:8010/api/health

# Check if services are running
docker ps | grep mep-

# Restart dashboard if needed
cd core && ./stop_dashboard_host.sh && ./start_dashboard_host.sh --background
```

**Common Dashboard Scenarios**:
- **Fresh Start**: After `./stop_admin.sh` and `./start_admin.sh`, dashboard shows empty state (normal)
- **Service Startup**: Use admin panel to start services, dashboard will update automatically
- **Service Failures**: Dashboard continues working, shows failed services as "unhealthy"
- **Network Issues**: Dashboard handles connection failures gracefully

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

## Service Access URLs

### Core Services
- **Dashboard**: http://localhost:8010
- **API Gateway**: http://localhost:8011
- **Core Processor**: http://localhost:8001
- **Document Router**: http://localhost:8002
- **Processing Pipeline**: http://localhost:8003
- **Storage Manager**: http://localhost:8004
- **Text Processor**: http://localhost:8005

### Infrastructure Services
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Elasticsearch**: http://localhost:9200
- **Qdrant**: http://localhost:6333
- **Neo4j**: http://localhost:7474
- **MinIO**: http://localhost:9000
- **n8n**: http://localhost:5678
- **Flowise**: http://localhost:3001

### Development UIs (Dev Profile)
- **pgAdmin**: http://localhost:8080
- **Redis Commander**: http://localhost:8081
- **Qdrant UI**: http://localhost:7070
- **MinIO Console**: http://localhost:9001

### Monitoring (Monitoring Profile)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3002

## Quick Commands

### Start All Services
```bash
cd mep_ainabox/services
./scripts/start-services.sh
```

### Start Development UIs
```bash
cd mep_ainabox/services
docker compose --profile dev up -d
```

### Start Monitoring
```bash
cd mep_ainabox/services
docker compose --profile monitoring up -d
```

### Start Dashboard (Host-based)
```bash
cd mep_ainabox/core
./start_dashboard.sh
```

### Start Admin Panel
```bash
cd mep_ainabox/core
./start_admin.sh
```

### Stop All Services
```bash
cd mep_ainabox
./stop_admin.sh
```

## Redis Commander UI

The Redis Commander UI is a web-based interface for managing Redis data. It's part of the development services profile.

### Starting Redis Commander
```bash
cd mep_ainabox/services
docker compose --profile dev up -d redis-commander
```

### Accessing Redis Commander
- **URL**: http://localhost:8081
- **Purpose**: Monitor and manage Redis data
- **Features**:
  - Browse Redis keys
  - View and edit values
  - Monitor memory usage
  - Execute Redis commands
  - Import/export data

### Redis Commander Configuration
The service is configured to connect to the Redis instance with:
- **Host**: redis (Docker service name)
- **Port**: 6379
- **Password**: Uses REDIS_PASSWORD from environment
- **Database**: 0 