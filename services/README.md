# MEP AI NABOX Services

This directory contains all the external services required by MEP AI NABOX, managed through Docker containers with external access and persistent data storage.

## 🏗️ Service Architecture

### Core Services
- **PostgreSQL**: Primary metadata database
- **Elasticsearch**: Full-text search engine
- **Qdrant**: Vector database for embeddings
- **Neo4j**: Graph database for relationships
- **Redis**: Caching and session management
- **MinIO**: Object storage for files and embeddings

### Development Services
- **pgAdmin**: PostgreSQL administration interface
- **Neo4j Browser**: Graph database interface
- **Redis Commander**: Redis management interface
- **MinIO Console**: Object storage management
- **Qdrant UI**: Vector database management interface (Custom HTML interface)

## 🚀 Quick Start

### 1. Start All Services
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f [service-name]
```

### 2. Access Services Externally

| Service | External Port | Internal Port | Access URL |
|---------|---------------|---------------|------------|
| PostgreSQL | 5432 | 5432 | `localhost:5432` |
| Elasticsearch | 9200 | 9200 | `http://localhost:9200` |
| Qdrant | 6333 | 6333 | `http://localhost:6333` |
| Neo4j | 7474 | 7474 | `http://localhost:7474` |
| Redis | 6379 | 6379 | `localhost:6379` |
| MinIO | 9000 | 9000 | `http://localhost:9000` |
| pgAdmin | 8080 | 80 | `http://localhost:8080` |
| Neo4j Browser | 7473 | 7473 | `http://localhost:7473` |
| Redis Commander | 8081 | 8081 | `http://localhost:8081` |
| MinIO Console | 9001 | 9001 | `http://localhost:9001` |
| Qdrant UI | 7070 | 7070 | `http://localhost:7070/index.html` |

### 3. Service Credentials

#### Qdrant UI
- **URL**: `http://localhost:7070/index.html`
- **Features**: 
  - View and manage collections
  - Search vectors
  - Add/delete points
  - API documentation
- **Start UI**: `./scripts/start-qdrant-ui.sh`

#### PostgreSQL
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `mep_ainabox`
- **Username**: `mep_user`
- **Password**: `mep_password`

#### Elasticsearch
- **URL**: `http://localhost:9200`
- **Username**: `elastic`
- **Password**: `elastic_password`

#### Qdrant
- **URL**: `http://localhost:6333`
- **API Key**: `qdrant_api_key`

#### Neo4j
- **URL**: `http://localhost:7474`
- **Username**: `neo4j`
- **Password**: `neo4j_password`

#### Redis
- **Host**: `localhost`
- **Port**: `6379`
- **Password**: `redis_password`

#### MinIO
- **URL**: `http://localhost:9000`
- **Access Key**: `minio_access_key`
- **Secret Key**: `minio_secret_key`

## 📁 Directory Structure

```
services/
├── README.md                    # This documentation
├── docker-compose.yml           # Main service orchestration
├── docker-compose.override.yml  # Development overrides
├── .env.example                 # Environment variables template
├── .env                         # Environment variables (create from .env.example)
├── volumes/                     # Persistent data storage
│   ├── postgres/                # PostgreSQL data
│   ├── elasticsearch/           # Elasticsearch data
│   ├── qdrant/                 # Qdrant data
│   ├── neo4j/                  # Neo4j data
│   ├── redis/                  # Redis data
│   └── minio/                  # MinIO data
├── config/                      # Service configurations
│   ├── postgres/               # PostgreSQL configuration
│   ├── elasticsearch/          # Elasticsearch configuration
│   ├── qdrant/                # Qdrant configuration
│   ├── neo4j/                 # Neo4j configuration
│   ├── redis/                 # Redis configuration
│   └── minio/                 # MinIO configuration
├── scripts/                     # Management scripts
│   ├── start-services.sh       # Start all services
│   ├── stop-services.sh        # Stop all services
│   ├── restart-services.sh     # Restart all services
│   ├── backup-services.sh      # Backup all data
│   ├── restore-services.sh     # Restore from backup
│   └── health-check.sh         # Check service health
└── monitoring/                  # Monitoring and logging
    ├── prometheus/             # Prometheus configuration
    ├── grafana/                # Grafana dashboards
    └── logs/                   # Service logs
```

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# PostgreSQL
POSTGRES_DB=mep_ainabox
POSTGRES_USER=mep_user
POSTGRES_PASSWORD=mep_password

# Elasticsearch
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=elastic_password

# Qdrant
QDRANT_API_KEY=qdrant_api_key

# Neo4j
NEO4J_PASSWORD=neo4j_password

# Redis
REDIS_PASSWORD=redis_password

# MinIO
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key
```

### Volume Mappings
All data is persisted to local directories:

- **PostgreSQL**: `./volumes/postgres/` → `/var/lib/postgresql/data`
- **Elasticsearch**: `./volumes/elasticsearch/` → `/usr/share/elasticsearch/data`
- **Qdrant**: `./volumes/qdrant/` → `/qdrant/storage`
- **Neo4j**: `./volumes/neo4j/` → `/data`
- **Redis**: `./volumes/redis/` → `/data`
- **MinIO**: `./volumes/minio/` → `/data`

## 🛠️ Management Commands

### Service Management
```bash
# Start all services
./scripts/start-services.sh

# Stop all services
./scripts/stop-services.sh

# Restart all services
./scripts/restart-services.sh

# Check service health
./scripts/health-check.sh
```

### Data Management
```bash
# Backup all data
./scripts/backup-services.sh

# Restore from backup
./scripts/restore-services.sh

# View service logs
docker-compose logs -f [service-name]
```

### Individual Service Management
```bash
# Start specific service
docker-compose up -d postgres

# Stop specific service
docker-compose stop elasticsearch

# Restart specific service
docker-compose restart qdrant

# View specific service logs

### Qdrant UI Management
```bash
# Start Qdrant UI
./scripts/start-qdrant-ui.sh

# Access the UI
open http://localhost:7070/index.html
```
docker-compose logs -f neo4j
```

## 🔍 Service Health Checks

### PostgreSQL
```bash
# Test connection
psql -h localhost -p 5432 -U mep_user -d mep_ainabox

# Check status
docker-compose exec postgres pg_isready
```

### Elasticsearch
```bash
# Check health
curl -u elastic:elastic_password http://localhost:9200/_cluster/health

# Check indices
curl -u elastic:elastic_password http://localhost:9200/_cat/indices
```

### Qdrant
```bash
# Check health
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections
```

### Neo4j
```bash
# Check health
curl http://localhost:7474/browser/

# Test connection
cypher-shell -u neo4j -p neo4j_password -a localhost:7687
```

### Redis
```bash
# Test connection
redis-cli -h localhost -p 6379 -a redis_password ping

# Check info
redis-cli -h localhost -p 6379 -a redis_password info
```

### MinIO
```bash
# Check health
curl http://localhost:9000/minio/health/live

# List buckets
mc alias set myminio http://localhost:9000 minio_access_key minio_secret_key
mc ls myminio
```

## 🔒 Security Considerations

### Network Security
- All services are accessible externally on localhost
- No internal Docker network isolation
- Services can be accessed from other systems on the network
- Consider firewall rules for production deployment

### Authentication
- All services use strong passwords
- API keys for Qdrant and MinIO
- Consider SSL/TLS for production
- Regular password rotation recommended

### Data Protection
- All data persisted to local volumes
- Regular backups recommended
- Consider encryption at rest for sensitive data
- Access control through service credentials

## 📊 Monitoring and Logging

### Prometheus Metrics
- Service metrics available on `/metrics` endpoints
- CPU, memory, disk usage monitoring
- Custom application metrics

### Grafana Dashboards
- Pre-configured dashboards for all services
- Real-time monitoring and alerting
- Historical data analysis

### Log Management
- Centralized logging to `./monitoring/logs/`
- Log rotation and retention policies
- Structured logging for easy parsing

## 🚀 Production Deployment

### Scaling Considerations
- Services can be scaled independently
- Load balancing for high availability
- Consider separate storage volumes for performance
- Monitor resource usage and adjust accordingly

### Backup Strategy
- Automated daily backups
- Point-in-time recovery capabilities
- Off-site backup storage
- Regular backup testing

### High Availability
- Service redundancy for critical components
- Health check monitoring
- Automatic failover capabilities
- Disaster recovery procedures

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Check disk space
df -h

# Check port conflicts
netstat -tulpn | grep :[port]
```

#### Connection Issues
```bash
# Test network connectivity
telnet localhost [port]

# Check service status
docker-compose ps

# Restart service
docker-compose restart [service-name]
```

#### Data Persistence Issues
```bash
# Check volume permissions
ls -la volumes/[service-name]/

# Fix permissions
sudo chown -R 1000:1000 volumes/[service-name]/

# Check volume mounting
docker-compose exec [service-name] ls -la /data
```

### Performance Tuning

#### PostgreSQL
- Adjust `shared_buffers` and `work_mem`
- Optimize query performance
- Regular VACUUM and ANALYZE

#### Elasticsearch
- Configure JVM heap size
- Optimize index settings
- Regular index maintenance

#### Qdrant
- Optimize collection settings
- Configure proper sharding
- Monitor vector search performance

#### Neo4j
- Adjust memory settings
- Optimize Cypher queries
- Configure proper indexing

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/index.html)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [MinIO Documentation](https://docs.min.io/) 