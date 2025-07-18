# Service Admin UIs Reference

This document provides a comprehensive reference for all service admin interfaces available in the MEP AI NABOX system.

## Quick Access

All service admin interfaces can be accessed through the **Admin Panel** at `http://localhost:8010/admin` in the "Service Admin Interfaces" section.

## Core Infrastructure Services

### 1. MinIO Console
- **URL**: http://localhost:9001
- **Description**: Object storage management interface
- **Purpose**: Manage buckets, files, and object storage
- **Default Credentials**: 
  - Username: `minio_access_key`
  - Password: `minio_secret_key`
- **Features**:
  - Bucket management
  - File upload/download
  - Access control
  - Storage analytics

### 2. Kibana
- **URL**: http://localhost:5601
- **Description**: Elasticsearch management and visualization
- **Purpose**: Search, analyze, and visualize data in Elasticsearch
- **Features**:
  - Data exploration
  - Dashboard creation
  - Index management
  - Search queries
  - Data visualization

### 3. Neo4j Browser
- **URL**: http://localhost:7474
- **Description**: Graph database interface
- **Purpose**: Query and visualize graph data
- **Default Credentials**:
  - Username: `neo4j`
  - Password: `neo4j_password`
- **Features**:
  - Cypher query execution
  - Graph visualization
  - Database management
  - Relationship exploration

## Application Services

### 4. n8n Workflows
- **URL**: http://localhost:5678
- **Description**: Workflow automation platform
- **Purpose**: Create and manage automated workflows
- **Features**:
  - Visual workflow builder
  - Node-based automation
  - API integrations
  - Workflow monitoring

### 5. Flowise
- **URL**: http://localhost:3001
- **Description**: LLM Flow Builder
- **Purpose**: Create and manage AI/LLM workflows
- **Default Credentials**:
  - Username: `admin`
  - Password: `admin123`
- **Features**:
  - LLM flow creation
  - Chat interface
  - API management
  - Flow deployment

## Development Tools (Dev Profile)

### 6. pgAdmin
- **URL**: http://localhost:8080
- **Description**: PostgreSQL administration
- **Purpose**: Database management and administration
- **Default Credentials**:
  - Email: `admin@mep.com`
  - Password: `admin_password`
- **Features**:
  - Database browsing
  - Query execution
  - Schema management
  - User management

### 7. Redis Commander
- **URL**: http://localhost:8081
- **Description**: Redis management interface
- **Purpose**: Monitor and manage Redis data
- **Features**:
  - Key browsing
  - Data inspection
  - Memory monitoring
  - Performance metrics

### 8. Elasticsearch Head
- **URL**: http://localhost:9100
- **Description**: Elasticsearch cluster management
- **Purpose**: Advanced Elasticsearch administration
- **Features**:
  - Cluster health monitoring
  - Index management
  - Query testing
  - Node information

## Monitoring Services (Monitoring Profile)

### 9. Prometheus
- **URL**: http://localhost:9090
- **Description**: Metrics collection and monitoring
- **Purpose**: System metrics and alerting
- **Features**:
  - Metrics visualization
  - Alert management
  - Query language
  - Service discovery

### 10. Grafana
- **URL**: http://localhost:3000
- **Description**: Monitoring dashboards
- **Purpose**: Advanced monitoring and visualization
- **Default Credentials**:
  - Username: `admin`
  - Password: `admin_password`
- **Features**:
  - Custom dashboards
  - Data visualization
  - Alerting
  - Multi-data source support

## Accessing Service UIs

### Method 1: Admin Panel (Recommended)
1. Navigate to `http://localhost:8010/admin`
2. Scroll down to "Service Admin Interfaces" section
3. Click "Open Interface" for any service

### Method 2: Direct URLs
Use the URLs listed above to access services directly.

### Method 3: Service Health Check
The admin panel also shows service status, helping you identify which services are running before accessing their UIs.

## Service Dependencies

### Infrastructure Services
- **PostgreSQL**: Required by most services
- **Redis**: Used for caching and sessions
- **Elasticsearch**: Search functionality
- **Qdrant**: Vector storage
- **MinIO**: File storage

### Application Services
- **n8n**: Depends on PostgreSQL and Redis
- **Flowise**: Depends on all infrastructure services

### Development Tools
- **pgAdmin**: Depends on PostgreSQL
- **Redis Commander**: Depends on Redis
- **Elasticsearch Head**: Depends on Elasticsearch

### Monitoring Tools
- **Prometheus**: Independent service
- **Grafana**: Depends on Prometheus

## Troubleshooting

### Service Not Accessible
1. Check if the service is running in the admin panel
2. Verify the port is not blocked by firewall
3. Check service logs for errors
4. Ensure dependencies are running

### Authentication Issues
1. Verify default credentials
2. Check environment variables
3. Restart the service if needed

### Port Conflicts
1. Check if ports are already in use
2. Modify docker-compose.yml if needed
3. Restart services after port changes

## Security Notes

- Default credentials should be changed in production
- Use environment variables for sensitive data
- Consider using reverse proxy for external access
- Enable SSL/TLS for production deployments

## Quick Commands

```bash
# Check service status
curl http://localhost:8010/api/admin/status

# Start all services
curl -X POST http://localhost:8010/api/admin/start-services

# Stop all services
curl -X POST http://localhost:8010/api/admin/stop-services

# Check specific service health
curl http://localhost:9000/minio/health/live  # MinIO
curl http://localhost:9200/_cluster/health    # Elasticsearch
curl http://localhost:6333/                   # Qdrant
```

## Environment Variables

Key environment variables for service configuration:

```bash
# MinIO
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key

# PostgreSQL
POSTGRES_USER=mep_user
POSTGRES_PASSWORD=mep_password
POSTGRES_DB=mep_ainabox

# Neo4j
NEO4J_PASSWORD=neo4j_password

# Flowise
FLOWISE_USERNAME=admin
FLOWISE_PASSWORD=admin123

# Redis
REDIS_PASSWORD=redis_password
```

For more detailed configuration, see the `env.example` file in the services directory. 