# MEP AI NABOX - Complete Startup Guide

This guide explains how to bring up all Docker containers and services in the mep_ainabox project.

## 🏗️ Project Architecture

The mep_ainabox project consists of two main components:

1. **Infrastructure Services** (`/services/`) - External services like databases, search engines, etc.
2. **Core System** (`/core/`) - The main application services that process documents

## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM available
- 20GB free disk space
- Linux/macOS/Windows with Docker support

## 🚀 Step-by-Step Startup Process

### Step 1: Clone and Navigate to Project
```bash
cd mep_ainabox
```

### Step 2: Set Up Environment Variables

#### For Infrastructure Services:
```bash
cd services
cp env.example .env
# Edit .env file with your preferred credentials
```

#### For Core System:
```bash
cd ../core
cp env.example .env
# Edit .env file with your preferred credentials
```

### Step 3: Start Infrastructure Services

The infrastructure services must be started first as the core system depends on them.

```bash
cd services

# Option A: Use the startup script (recommended)
./scripts/start-services.sh

# Option B: Manual startup
docker compose up -d

# Verify services are running
docker compose ps
```

**Infrastructure Services Started:**
- PostgreSQL (port 5432) - Primary database
- Elasticsearch (port 9200) - Search engine
- Qdrant (port 6333) - Vector database
- Neo4j (port 7474) - Graph database
- Redis (port 6379) - Caching
- MinIO (port 9000) - Object storage
- Kibana (port 5601) - Elasticsearch UI
- pgAdmin (port 8080) - PostgreSQL UI
- Redis Commander (port 8081) - Redis UI
- MinIO Console (port 9001) - MinIO UI
- n8n (port 5678) - Workflow automation
- Flowise (port 3001) - LLM Flow Builder

### Step 4: Wait for Infrastructure Services to be Ready

```bash
# Check service health
./scripts/health-check.sh

# Or manually check key services
curl http://localhost:9200/_cluster/health  # Elasticsearch
curl http://localhost:6333/collections      # Qdrant
curl http://localhost:7474/db/data/         # Neo4j
```

**Expected wait time:** 2-5 minutes for all services to be fully ready.

### Step 5: Start Core System

```bash
cd ../core

# Option A: Use the startup script (recommended)
./start.sh

# Option B: Manual startup
docker compose up -d

# Verify services are running
docker compose ps
```

**Core Services Started:**
- API Gateway (port 8000) - Main entry point
- Core Processor (port 8001) - Document processing orchestrator
- Document Router (port 8002) - Intelligent document routing
- Processing Pipeline (port 8003) - Document processing workflow
- Storage Manager (port 8004) - Data storage interface
- Text Processor (port 8005) - Text extraction
- Metadata Processor (port 8006) - Metadata extraction
- Embedding Processor (port 8007) - Vector embeddings
- Entity Processor (port 8008) - Entity extraction
- File Watcher (port 8009) - File monitoring
- Dashboard (port 8010) - Web monitoring interface

### Step 6: Verify All Services

```bash
# Check core system health
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Core Processor
curl http://localhost:8002/health  # Document Router
curl http://localhost:8003/health  # Processing Pipeline
curl http://localhost:8004/health  # Storage Manager

# Check dashboard
curl http://localhost:8010/api/health
```

## 🌐 Access URLs

### Core Application
- **API Gateway**: http://localhost:8000
- **Dashboard**: http://localhost:8010
- **Service Details**: http://localhost:8010/service/file-watcher

### Infrastructure Services
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **Qdrant**: http://localhost:6333
- **Neo4j Browser**: http://localhost:7474
- **MinIO Console**: http://localhost:9001
- **Redis Commander**: http://localhost:8081
- **pgAdmin**: http://localhost:8080
- **n8n**: http://localhost:5678
- **Flowise**: http://localhost:3001

## 🔧 Management Commands

### Start All Services
```bash
# Start infrastructure services
cd services && ./scripts/start-services.sh

# Start core system
cd ../core && ./start.sh
```

### Stop All Services
```bash
# Stop core system
cd core && docker compose down

# Stop infrastructure services
cd ../services && docker compose down
```

### Restart Services
```bash
# Restart core system
cd core && docker compose restart

# Restart infrastructure services
cd ../services && docker compose restart
```

### View Logs
```bash
# Core system logs
cd core && docker compose logs -f

# Infrastructure services logs
cd services && docker compose logs -f

# Specific service logs
docker compose logs -f [service-name]
```

### Health Checks
```bash
# Infrastructure services health
cd services && ./scripts/health-check.sh

# Core system health
cd ../core && curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker daemon is running
2. **Port conflicts**: Ensure ports are not used by other applications
3. **Memory issues**: Increase Docker memory allocation
4. **Network issues**: Check if `mep-services-network` exists

### Reset Everything
```bash
# Stop and remove all containers
cd services && docker compose down -v
cd ../core && docker compose down -v

# Remove volumes (WARNING: This deletes all data)
docker volume prune

# Restart from scratch
cd services && ./scripts/start-services.sh
cd ../core && ./start.sh
```

### Check Resource Usage
```bash
# View running containers
docker ps

# Check resource usage
docker stats

# Check disk usage
docker system df
```

## 📊 Monitoring

### Dashboard Features
- **Service Health**: Real-time status of all services
- **Configuration**: View and edit service configurations
- **Logs**: Access service logs with filtering
- **Metrics**: Monitor resource usage and performance

### External Monitoring
- **Kibana**: Elasticsearch monitoring and visualization
- **Grafana**: System metrics and dashboards
- **Prometheus**: Metrics collection and alerting

## 🔐 Default Credentials

### Database Services
- **PostgreSQL**: mep_user / mep_password
- **Redis**: redis_password
- **Neo4j**: neo4j / neo4j_password

### Storage Services
- **MinIO**: minio_access_key / minio_secret_key
- **Qdrant**: qdrant_api_key

### Management UIs
- **pgAdmin**: admin / admin
- **Kibana**: elastic / elastic_password

## 📝 Next Steps

After successful startup:

1. **Upload Documents**: Place files in `core/watch_folder/`
2. **Monitor Processing**: Use the dashboard at http://localhost:8010
3. **Configure Services**: Edit configurations in `core/config/`
4. **Set Up Workflows**: Use n8n at http://localhost:5678
5. **Build LLM Flows**: Use Flowise at http://localhost:3001

## 🆘 Support

If you encounter issues:

1. Check the logs: `docker compose logs -f [service-name]`
2. Verify network connectivity: `docker network ls`
3. Check resource usage: `docker stats`
4. Review this guide and the individual service READMEs
5. Check the project documentation in `/docs/`

---

**Total startup time:** 5-10 minutes for a fresh installation
**Memory usage:** ~4-6GB RAM
**Disk usage:** ~2-5GB (depending on data volume) 