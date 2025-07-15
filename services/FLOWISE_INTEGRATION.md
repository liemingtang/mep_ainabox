# Flowise Integration for MEP AI NABOX

## Overview

Flowise has been successfully integrated into the MEP AI NABOX services stack. Flowise is a drag & drop UI tool for building LLM flows and AI agents, providing a visual interface for creating complex AI workflows.

## Service Configuration

### Docker Service
- **Image**: `flowiseai/flowise:latest`
- **Container Name**: `mep-flowise`
- **Port**: `3001:3000` (host:container)
- **Health Check**: HTTP endpoint `/` (root page)
- **Status**: ✅ Healthy

### Environment Variables
The Flowise service is configured with the following environment variables:

#### Basic Configuration
- `PORT=3000` - Internal port
- `HOST=0.0.0.0` - Bind to all interfaces
- `FLOWISE_USERNAME=admin` - Default username
- `FLOWISE_PASSWORD=admin123` - Default password
- `SECRETKEY=flowise_secret_key_123` - Encryption key
- `LOG_LEVEL=info` - Logging level
- `DATABASE_TYPE=sqlite` - Database type (can be changed to postgres)

#### External Service Connections
- **Redis**: `redis:6379` - Session management and caching
- **Qdrant**: `http://qdrant:6333` - Vector database
- **Elasticsearch**: `http://elasticsearch:9200` - Search engine
- **Neo4j**: `bolt://neo4j:7687` - Graph database
- **MinIO**: `minio:9000` - Object storage
- **PostgreSQL**: `postgres:5432` - Primary database (optional)

#### API Credentials
- `OPENAI_API_KEY` - OpenAI API access
- `ANTHROPIC_API_KEY` - Anthropic API access
- `GOOGLE_API_KEY` - Google API access
- `HUGGINGFACE_API_TOKEN` - Hugging Face API access

## Access Information

### Web Interface
- **URL**: http://localhost:3001
- **Username**: admin
- **Password**: admin123

### API Access
- **Base URL**: http://localhost:3001/api/v1
- **API Key**: `mep-flowise-api-key-123` (configured in api.json)

## Integration with Other Services

### Database Integration
Flowise can use either SQLite (default) or PostgreSQL:
- **SQLite**: Stored in `./volumes/flowise/database/`
- **PostgreSQL**: Uses the existing `mep-postgres` service

### Vector Database
- **Qdrant**: Available for storing and querying embeddings
- **Elasticsearch**: Available for full-text search capabilities

### Object Storage
- **MinIO**: Available for storing files, documents, and embeddings

### Graph Database
- **Neo4j**: Available for storing and querying knowledge graphs

### Caching
- **Redis**: Used for session management and caching

## File Structure

```
services/
├── docker-compose.yml          # Main service configuration
├── config/
│   └── flowise/
│       └── flowise.json        # Flowise configuration
├── volumes/
│   └── flowise/
│       ├── api.json            # API key configuration
│       ├── credentials.json    # External API credentials
│       ├── database/           # SQLite database files
│       ├── logs/               # Application logs
│       └── custom/             # Custom components
└── scripts/
    ├── start-services.sh       # Updated to include Flowise
    ├── stop-services.sh        # Stops all services including Flowise
    └── health-check.sh         # Updated to check Flowise health
```

## Usage Examples

### Starting Services
```bash
# Start all services including Flowise
./scripts/start-services.sh

# Start with development tools
./scripts/start-services.sh --dev

# Start with monitoring
./scripts/start-services.sh --monitoring
```

### Health Check
```bash
# Check all services health
./scripts/health-check.sh

# Check Flowise specifically
curl -f http://localhost:3001/
```

### API Usage
```bash
# List chatflows (requires authentication)
curl -H "Authorization: Bearer mep-flowise-api-key-123" \
     http://localhost:3001/api/v1/chatflows

# Create a new chatflow
curl -X POST \
     -H "Authorization: Bearer mep-flowise-api-key-123" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Flow", "flowData": {...}}' \
     http://localhost:3001/api/v1/chatflows
```

## Security Considerations

1. **Default Credentials**: Change the default username/password in production
2. **API Keys**: Store sensitive API keys in environment variables
3. **Network Access**: Flowise is accessible on localhost:3001
4. **Database**: Consider using PostgreSQL for production deployments

## Troubleshooting

### Common Issues

1. **Health Check Failing**: 
   - Check if Flowise is accessible at http://localhost:3001
   - Verify the container logs: `docker compose logs flowise`

2. **Service Dependencies**:
   - Ensure Redis, Qdrant, and other services are running
   - Check service connectivity within the Docker network

3. **Port Conflicts**:
   - Flowise uses port 3001 (mapped from container port 3000)
   - Grafana uses port 3000 (no conflict)

### Logs
```bash
# View Flowise logs
docker compose logs flowise

# Follow logs in real-time
docker compose logs -f flowise

# View specific number of lines
docker compose logs --tail=50 flowise
```

## Next Steps

1. **Custom Components**: Add custom nodes and components in `./volumes/flowise/custom/`
2. **Database Migration**: Consider migrating from SQLite to PostgreSQL for production
3. **Authentication**: Implement proper authentication and authorization
4. **Monitoring**: Add Flowise metrics to Prometheus/Grafana monitoring
5. **Backup**: Implement regular backups of Flowise data and configurations

## Support

For Flowise-specific issues, refer to:
- [Flowise Documentation](https://docs.flowiseai.com/)
- [Flowise GitHub](https://github.com/FlowiseAI/Flowise)
- [Flowise Community](https://discord.gg/jbaHfsRVBd) 