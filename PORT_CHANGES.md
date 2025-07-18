# Port Configuration Changes

## Overview
To avoid port conflicts with other services, the following port changes have been made:

## Changed Ports

### API Gateway
- **Old Port**: 8000
- **New Port**: 8011
- **Reason**: Conflict with other services
- **Access**: http://localhost:8011

### Grafana
- **Old Port**: 3000
- **New Port**: 3002
- **Reason**: Conflict with Flowise (port 3001)
- **Access**: http://localhost:3002

## Current Port Assignments

### Core Services
- **Dashboard**: 8010
- **API Gateway**: 8011
- **Core Processor**: 8001
- **Document Router**: 8002
- **Processing Pipeline**: 8003
- **Storage Manager**: 8004
- **Text Processor**: 8005

### Infrastructure Services
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Elasticsearch**: 9200
- **Kibana**: 5601
- **Qdrant**: 6333
- **Neo4j**: 7474 (HTTP), 7687 (Bolt)
- **MinIO**: 9000 (API), 9001 (Console)
- **Flowise**: 3001

### Development Services
- **pgAdmin**: 8080
- **Elasticsearch Head**: 9100
- **Redis Commander**: 8081
- **Qdrant UI**: 7070

### Monitoring Services (Monitoring Profile)
- **Prometheus**: 9090
- **Grafana**: 3002

## Starting Monitoring Services

To start Prometheus and Grafana (which are in the monitoring profile):

```bash
cd mep_ainabox/services
docker compose --profile monitoring up -d prometheus grafana
```

## Verification

You can verify the services are running correctly by:

1. **Dashboard**: http://localhost:8010
2. **API Gateway**: http://localhost:8011/health
3. **Grafana**: http://localhost:3002 (when monitoring profile is active)

## Notes

- The monitoring services (Prometheus and Grafana) are not started by default
- They require the `--profile monitoring` flag to be started
- All port changes have been reflected in the dashboard configuration
- Service admin UIs have been updated with the new ports 