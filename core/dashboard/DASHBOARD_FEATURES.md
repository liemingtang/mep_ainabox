# MDIS Dashboard Features

## Overview

The MDIS Dashboard provides comprehensive monitoring and management capabilities for all services in the MEP AI NABOX system. It displays real-time logs, configuration, and metrics for each service.

## Accessing the Dashboard

The dashboard is available at: `http://localhost:8010`

## Features

### 1. Service Health Monitoring
- **Real-time health checks** for all services
- **Status indicators** (healthy, unhealthy, error)
- **Response time monitoring**
- **Service uptime tracking**

### 2. Log Management
- **Real-time log viewing** for each service
- **Configurable log line count** (50, 100, 200, 500 lines)
- **Log level highlighting** (error, warning, info)
- **Docker container log integration**
- **Automatic log refresh**

### 3. Configuration Management
- **Service-specific configuration display**
- **Environment variable monitoring**
- **Configuration file content viewing**
- **Sensitive data masking** (passwords, keys, tokens)
- **Configuration categorization**

### 4. Metrics and Performance
- **Service performance metrics**
- **Docker container statistics** (CPU, Memory, Network)
- **Database statistics** (Elasticsearch, Qdrant, Neo4j)
- **Processing pipeline metrics**
- **Real-time data visualization**

## Supported Services

### Core Processing Services
- **API Gateway** (Port 8000) - Unified entry point
- **Core Processor** (Port 8001) - Main orchestrator
- **Document Router** (Port 8002) - Intelligent routing
- **Processing Pipeline** (Port 8003) - Workflow orchestration
- **Storage Manager** (Port 8004) - Data storage interface
- **Text Processor** (Port 8005) - Text extraction
- **Metadata Processor** (Port 8006) - Metadata extraction
- **Embedding Processor** (Port 8007) - Vector embeddings
- **Entity Processor** (Port 8008) - Entity extraction
- **File Watcher** (Port 8009) - Folder monitoring

### Infrastructure Services
- **PostgreSQL** (Port 5432) - Primary database
- **Elasticsearch** (Port 9200) - Search engine
- **Qdrant** (Port 6333) - Vector database
- **Neo4j** (Port 7474) - Graph database
- **Redis** (Port 6379) - Caching layer
- **MinIO** (Port 9000) - Object storage
- **Flowise** (Port 3001) - LLM flow builder

## API Endpoints

### Health and Status
- `GET /api/health` - Overall system health
- `GET /api/services` - All services status
- `GET /api/service/{service_name}` - Specific service details

### Logs
- `GET /api/service/{service_name}/logs?lines=50` - Service logs

### Configuration
- `GET /api/service/{service_name}/configuration` - Service configuration
- `GET /api/configuration` - Global configuration
- `POST /api/configuration` - Update configuration

### Metrics
- `GET /api/service/{service_name}/metrics` - Service metrics
- `GET /api/stats` - Dashboard statistics

## Log Sources

The dashboard retrieves logs from multiple sources in order of priority:

1. **Docker Container Logs** (Primary)
   - Uses `docker logs` command
   - Most reliable source
   - Real-time access

2. **Local Log Files** (Fallback)
   - Service-specific log files
   - Application logs
   - Error logs

3. **Alternative Locations** (Secondary)
   - Common log directories
   - Relative paths
   - Standard locations

## Configuration Sources

Configuration is retrieved from:

1. **Global Configuration**
   - Dashboard configuration file
   - Environment variables
   - System settings

2. **Service-Specific Configuration**
   - Configuration files within containers
   - Environment variables per service
   - Docker container inspection

3. **Service Configuration Files**
   - YAML configuration files
   - JSON configuration files
   - Service-specific configs

## Metrics Sources

Metrics are collected from:

1. **Service Endpoints**
   - `/metrics` endpoints
   - `/health` endpoints
   - `/stats` endpoints

2. **Docker Container Stats**
   - CPU usage
   - Memory usage
   - Network I/O
   - Container status

3. **Database Statistics**
   - Elasticsearch cluster health
   - Qdrant collections
   - Neo4j database info

## Security Features

- **Sensitive data masking** for passwords, keys, and tokens
- **Read-only configuration viewing**
- **Secure log access**
- **Container isolation**

## Troubleshooting

### Common Issues

1. **No Logs Available**
   - Check if Docker containers are running
   - Verify container names match expected names
   - Check Docker permissions

2. **Configuration Not Loading**
   - Ensure configuration files exist
   - Check file permissions
   - Verify container access

3. **Metrics Not Available**
   - Check service endpoints
   - Verify network connectivity
   - Check service health

### Testing

Use the test script to verify dashboard functionality:

```bash
cd mep_ainabox/core/dashboard
python test_dashboard.py
```

### Manual Log Access

If dashboard logs are not working, access logs manually:

```bash
# Docker container logs
docker logs mep-core-processor --tail 50

# Local log files
tail -f logs/core-processor.log
```

## Development

### Adding New Services

To add a new service to the dashboard:

1. Update `SERVICE_INFO` in `main.py`
2. Add service endpoints
3. Configure log paths
4. Set up metrics endpoints
5. Update templates if needed

### Customizing Display

- Modify `service_detail.html` for UI changes
- Update CSS in `dashboard.css` for styling
- Add new API endpoints in `main.py`

## Performance Considerations

- **Log retrieval** is limited to prevent memory issues
- **Configuration files** are truncated for display
- **Metrics** are cached to reduce API calls
- **Docker commands** have timeouts to prevent hanging

## Future Enhancements

- **Real-time log streaming**
- **Configuration editing**
- **Service restart capabilities**
- **Alert management**
- **Performance dashboards**
- **Custom metrics**
- **Log search and filtering** 