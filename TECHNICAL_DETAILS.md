# Technical Details

This document provides detailed technical information about the MEP AI NABOX system, including recent fixes, improvements, and implementation details.

## 🔧 Recent Technical Fixes

### UUID Type Handling

#### Problem
The system was experiencing UUID type mismatch errors in SQL queries, where PostgreSQL expected string values but received UUID objects.

#### Solution
Implemented comprehensive UUID to string conversion across all database operations:

```python
# Before (causing errors)
document_id = uuid.uuid4()
query = "SELECT * FROM documents WHERE id = $1"
await conn.execute(query, document_id)

# After (fixed)
document_id = str(uuid.uuid4())
query = "SELECT * FROM documents WHERE id = $1"
await conn.execute(query, document_id)
```

#### Files Modified
- `core_processor/app/services/document_service.py`
- `core_processor/app/services/processing_service.py`
- `core_processor/app/api/endpoints/documents.py`
- `core_processor/app/api/endpoints/processing.py`

### JSON Serialization for Metadata

#### Problem
Metadata fields were being stored as Python dictionaries, but the database expected JSON strings.

#### Solution
Implemented JSON serialization/deserialization for metadata fields:

```python
# Before
metadata = {"key": "value"}
await conn.execute("INSERT INTO documents (metadata) VALUES ($1)", metadata)

# After
import json
metadata = json.dumps({"key": "value"})
await conn.execute("INSERT INTO documents (metadata) VALUES ($1)", metadata)
```

#### Files Modified
- `core_processor/app/services/document_service.py`
- `core_processor/app/models/document.py`

### Database Connection Management

#### Problem
Services were failing to establish proper database connections due to configuration issues.

#### Solution
Implemented proper connection pooling and configuration:

```python
# PostgreSQL Connection Pool
async def init_postgres_pool():
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        min_size=5,
        max_size=20
    )

# Elasticsearch Client
def init_elasticsearch_client():
    return Elasticsearch(
        [f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )

# Qdrant Client with API Key
def init_qdrant_client():
    return AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
        timeout=30
    )
```

### Service Startup Sequence

#### Problem
Services were starting before their dependencies were ready, causing connection failures.

#### Solution
Implemented proper dependency checking and startup sequence:

```bash
#!/bin/bash
# start.sh - Improved startup script

echo "Starting Core Processor initialization..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER; do
    sleep 2
done
echo "PostgreSQL is ready!"

# Wait for Elasticsearch
echo "Waiting for Elasticsearch to be ready..."
until curl -s http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cluster/health | grep -q '"status":"green"\|"status":"yellow"'; do
    sleep 2
done
echo "Elasticsearch is ready!"

# Wait for Qdrant
echo "Waiting for Qdrant to be ready..."
until curl -s http://$QDRANT_HOST:$QDRANT_PORT/collections | grep -q '"status":"ok"'; do
    sleep 2
done
echo "Qdrant is ready!"

# Initialize database schema
echo "Initializing database schema..."
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f /app/app/database/schema.sql

echo "Core Processor initialization completed!"
```

## 🗄️ Database Schema

### PostgreSQL Schema

The system uses PostgreSQL with the following key features:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table with UUID primary key
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    metadata JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing jobs table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document content table
CREATE TABLE IF NOT EXISTS document_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content_type VARCHAR(50),
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document embeddings table
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    model_name VARCHAR(100),
    embedding_vector REAL[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document entities table
CREATE TABLE IF NOT EXISTS document_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(50),
    entity_value TEXT,
    confidence REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document relationships table
CREATE TABLE IF NOT EXISTS document_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50),
    confidence REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes for Performance

```sql
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(file_type);
CREATE INDEX IF NOT EXISTS idx_documents_company ON documents USING GIN ((metadata->>'company'));
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents USING GIN ((metadata->>'year'));
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents USING GIN ((metadata->>'file_hash'));

-- Processing jobs indexes
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);

-- Document embeddings indexes
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_model ON document_embeddings(model_name);

-- Document entities indexes
CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_document_entities_type ON document_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_document_entities_value ON document_entities(entity_value);

-- Document relationships indexes
CREATE INDEX IF NOT EXISTS idx_document_relationships_source ON document_relationships(source_document_id);
CREATE INDEX IF NOT EXISTS idx_document_relationships_target ON document_relationships(target_document_id);
CREATE INDEX IF NOT EXISTS idx_document_relationships_type ON document_relationships(relationship_type);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_documents_filename_fts ON documents USING GIN (to_tsvector('english', filename));
CREATE INDEX IF NOT EXISTS idx_document_content_text_fts ON document_content USING GIN (to_tsvector('english', content));
```

## 🔄 Service Communication

### Internal Network Architecture

Services communicate over a dedicated Docker network:

```yaml
# docker-compose.yml
networks:
  mep-services-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  core-processor:
    networks:
      - mep-services-network
    depends_on:
      - postgres
      - elasticsearch
      - qdrant
      - neo4j
      - redis
      - minio
```

### Health Check Implementation

All services implement health checks:

```python
# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Check database connections
        await check_database_health()
        
        # Check external services
        await check_external_services()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "postgres": "healthy",
                "elasticsearch": "healthy",
                "qdrant": "healthy",
                "neo4j": "healthy",
                "redis": "healthy",
                "minio": "healthy"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

## 📊 Monitoring and Observability

### Prometheus Metrics

All services expose Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
document_uploads = Counter('document_uploads_total', 'Total document uploads')
processing_jobs = Counter('processing_jobs_total', 'Total processing jobs')
processing_duration = Histogram('processing_duration_seconds', 'Processing duration')
active_jobs = Gauge('active_processing_jobs', 'Currently active processing jobs')

# Metrics usage
@app.post("/documents/upload")
async def upload_document():
    document_uploads.inc()
    start_time = time.time()
    
    try:
        # Process document
        result = await process_document()
        
        # Record metrics
        processing_duration.observe(time.time() - start_time)
        return result
    except Exception as e:
        # Record error metrics
        processing_errors.inc()
        raise
```

### Structured Logging

All services use structured JSON logging:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
logger.info("Document processed", 
    document_id=str(document_id),
    processing_time=processing_time,
    status="completed"
)
```

## 🔒 Security Implementation

### API Key Management

External service API keys are securely managed:

```python
# Environment variable loading
class Settings(BaseSettings):
    QDRANT_API_KEY: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    HUGGINGFACE_API_TOKEN: str
    
    class Config:
        env_file = ".env"

# Secure client initialization
def init_qdrant_client():
    return AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
        timeout=30
    )
```

### Service-to-Service Security

Services communicate over isolated Docker networks with no external access:

```yaml
# docker-compose.yml
services:
  core-processor:
    networks:
      - mep-services-network
    expose:
      - "8001"  # Only expose to internal network
    ports:
      - "127.0.0.1:8001:8001"  # Only bind to localhost
```

## 🧪 Testing Strategy

### Test Scripts

The system includes comprehensive test scripts:

```python
# test_simple_upload.py
async def test_document_upload():
    """Test basic document upload functionality"""
    
    # Test data
    test_document = {
        "filename": "test_document.pdf",
        "file_path": "/app/documents/test_document.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "metadata": {"source": "test", "category": "documentation"}
    }
    
    # Upload document
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/documents/upload",
            json=test_document
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "document_id" in result
        
        # Verify document was stored
        doc_response = await client.get(
            f"http://localhost:8001/documents/{result['document_id']}"
        )
        assert doc_response.status_code == 200
```

### Health Check Tests

```python
# test_system.py
async def test_service_health():
    """Test all service health endpoints"""
    
    services = [
        ("API Gateway", "http://localhost:8000/health"),
        ("Core Processor", "http://localhost:8001/health"),
        ("Document Router", "http://localhost:8002/health"),
        ("Processing Pipeline", "http://localhost:8003/health"),
        ("Storage Manager", "http://localhost:8004/health"),
    ]
    
    for service_name, url in services:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 200, f"{service_name} health check failed"
            
            data = response.json()
            assert data["status"] == "healthy", f"{service_name} is not healthy"
```

## 🚀 Performance Optimizations

### Database Connection Pooling

```python
# PostgreSQL connection pool
async def init_postgres_pool():
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        min_size=5,      # Minimum connections
        max_size=20,     # Maximum connections
        command_timeout=60,
        server_settings={
            'application_name': 'mep_ainabox_core_processor'
        }
    )
```

### Caching Strategy

```python
# Redis caching
async def get_cached_document(document_id: str):
    """Get document from cache or database"""
    
    # Try cache first
    cached = await redis.get(f"document:{document_id}")
    if cached:
        return json.loads(cached)
    
    # Get from database
    document = await get_document_from_db(document_id)
    
    # Cache for 1 hour
    await redis.setex(
        f"document:{document_id}",
        3600,  # 1 hour
        json.dumps(document)
    )
    
    return document
```

## 🔄 Deployment Considerations

### Environment Configuration

```bash
# .env file structure
# System Configuration
SYSTEM_ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mep_ainabox
POSTGRES_USER=mep_user
POSTGRES_PASSWORD=mep_password

# External Services
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=your-qdrant-api-key

# API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
HUGGINGFACE_API_TOKEN=your-huggingface-api-token
```

### Resource Requirements

```yaml
# docker-compose.yml resource limits
services:
  core-processor:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## 📚 Additional Resources

- [Architecture Documentation](README_architecture.md)
- [API Documentation](core/api_documentation.md)
- [Deployment Guide](core/deployment_guide.md)
- [Changelog](CHANGELOG.md)
- [Troubleshooting Guide](core/README.md#troubleshooting) 