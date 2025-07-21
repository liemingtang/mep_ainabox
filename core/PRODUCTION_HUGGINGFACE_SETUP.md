# Production Setup with HuggingFace Embeddings

## Overview

This document describes how to configure the production system to use HuggingFace as the default embedding provider for processing new files from the watch folder or scan_folder script.

## Quick Setup

### Automated Setup

Use the provided setup script for quick configuration:

```bash
cd mep_ainabox/core

# Full setup with Ollama (recommended for production)
./setup_production_huggingface.sh

# Setup without Ollama (if you only need HuggingFace)
./setup_production_huggingface.sh --skip-ollama

# Setup with model initialization
./setup_production_huggingface.sh --init-models

# Setup with tests
./setup_production_huggingface.sh --test
```

### Manual Setup

If you prefer manual setup:

```bash
cd mep_ainabox/core

# 1. Stop existing services
docker compose down

# 2. Start services with HuggingFace configuration
docker compose up -d

# 3. Initialize HuggingFace models
docker compose exec embedding-processor python init_huggingface.py

# 4. Test the setup
docker compose exec embedding-processor python test_embeddings.py
```

## Configuration Changes

### Docker Compose Configuration

The main `docker-compose.yml` has been updated with:

```yaml
embedding-processor:
  environment:
    # Embedding provider configuration
    - EMBEDDING_PROVIDER=huggingface  # Changed from "ollama"
    - HF_DEFAULT_MODEL=sentence-transformers/all-MiniLM-L6-v2
    - HF_CACHE_DIR=/app/cache/huggingface
    - HF_DEVICE=cpu
    - HF_BATCH_SIZE=32
  volumes:
    - huggingface_cache:/app/cache/huggingface  # Added HuggingFace cache
  depends_on:
    - processing-pipeline  # Removed ollama dependency

processing-pipeline:
  environment:
    - EMBEDDING_PROVIDER=huggingface  # Added provider configuration

volumes:
  huggingface_cache:  # Added HuggingFace cache volume
    driver: local
```

### Processing Pipeline Updates

The processing pipeline now passes the provider parameter to the embedding processor:

```python
# In processing_pipeline/main.py
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface")

async def generate_embeddings(document_id: str, text_content: str, metadata: Dict[str, Any] = None):
    response = await client.post(
        f"{EMBEDDING_PROCESSOR_URL}/process",
        json={
            "document_id": document_id,
            "text_content": text_content,
            "metadata": metadata or {},
            "provider": EMBEDDING_PROVIDER  # Added provider parameter
        }
    )
```

## File Processing Flow

### Watch Folder Processing

1. **File Detection**: File watcher monitors `./watch_folder/`
2. **Document Upload**: Files are sent to core processor
3. **Text Extraction**: Processing pipeline extracts text
4. **Embedding Generation**: Uses HuggingFace by default
5. **Storage**: Embeddings stored in Qdrant

### Scan Folder Script

The `folder_scanner.py` script also uses the same flow:

```bash
# Scan a folder for processing
curl -X POST http://localhost:8009/api/v1/watch/scan-folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/documents",
    "recursive": true,
    "max_depth": 3,
    "concurrent_limit": 5
  }'
```

## Environment Variables

### Required Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `huggingface` | Embedding provider (huggingface/ollama) |
| `HF_DEFAULT_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Default HuggingFace model |
| `HF_CACHE_DIR` | `/app/cache/huggingface` | HuggingFace model cache directory |
| `HF_DEVICE` | `cpu` | Device for HuggingFace models |
| `HF_BATCH_SIZE` | `32` | Batch size for processing |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WATCH_FOLDER_PATH` | `./watch_folder` | Path to watch folder |
| `PROCESSED_DOCUMENTS_PATH` | `./processed` | Path for processed documents |
| `TEMP_PROCESSING_PATH` | `./temp` | Path for temporary files |

## Service Health Checks

### Check Service Status

```bash
# Embedding processor
curl http://localhost:8007/health

# Processing pipeline
curl http://localhost:8003/health

# File watcher
curl http://localhost:8009/health

# Core processor
curl http://localhost:8001/health
```

### Monitor Logs

```bash
# All services
docker compose logs -f

# Specific services
docker compose logs -f embedding-processor
docker compose logs -f file-watcher
docker compose logs -f processing-pipeline
```

## Testing the Setup

### Test Embedding Generation

```bash
# Test single embedding
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "provider": "huggingface"
  }'

# Test document processing
curl -X POST http://localhost:8007/process \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test123",
    "text_content": "This is a test document for processing.",
    "metadata": {"source": "test"}
  }'
```

### Test File Processing

```bash
# 1. Add a test file to watch folder
echo "This is a test document." > ./watch_folder/test.txt

# 2. Check processing status
curl http://localhost:8009/api/v1/watch/status

# 3. Check processed files
curl http://localhost:8009/api/v1/watch/processed
```

### Run Comprehensive Tests

```bash
# Run the test suite
docker compose exec embedding-processor python test_embeddings.py
```

## Performance Optimization

### HuggingFace Model Selection

| Use Case | Recommended Model | Dimensions | Speed | Quality |
|----------|------------------|------------|-------|---------|
| **Fast Processing** | `paraphrase-MiniLM-L3-v2` | 384 | Very Fast | Good |
| **Balanced** | `all-MiniLM-L6-v2` | 384 | Fast | Good |
| **High Quality** | `all-mpnet-base-v2` | 768 | Medium | High |
| **Best Quality** | `e5-large-v2` | 1024 | Slow | Excellent |

### Configuration Tuning

```bash
# For faster processing
export HF_BATCH_SIZE=64
export HF_DEFAULT_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2

# For better quality
export HF_DEFAULT_MODEL=sentence-transformers/all-mpnet-base-v2
export HF_BATCH_SIZE=16

# For GPU acceleration (if available)
export HF_DEVICE=cuda
```

## Troubleshooting

### Common Issues

#### 1. HuggingFace Model Download Fails

```bash
# Check internet connection
curl -I https://huggingface.co

# Check cache directory permissions
ls -la /app/cache/huggingface

# Manually download model
docker compose exec embedding-processor python init_huggingface.py
```

#### 2. Memory Issues

```bash
# Use smaller model
export HF_DEFAULT_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2

# Reduce batch size
export HF_BATCH_SIZE=16

# Increase Docker memory limits
# Edit docker-compose.yml and add memory limits
```

#### 3. Slow Processing

```bash
# Use faster model
export HF_DEFAULT_MODEL=sentence-transformers/paraphrase-MiniLM-L3-v2

# Increase batch size
export HF_BATCH_SIZE=64

# Enable GPU acceleration (if available)
export HF_DEVICE=cuda
```

### Log Analysis

```bash
# Check embedding processor logs
docker compose logs embedding-processor | grep -i error

# Check processing pipeline logs
docker compose logs processing-pipeline | grep -i error

# Check file watcher logs
docker compose logs file-watcher | grep -i error
```

## Migration from Ollama

### If You Were Previously Using Ollama

1. **Backup Data**: Ensure your Qdrant data is backed up
2. **Update Configuration**: The system now uses HuggingFace by default
3. **Test Processing**: Verify that new files are processed correctly
4. **Monitor Performance**: Compare processing speed and quality

### Switching Back to Ollama

If you need to switch back to Ollama:

```bash
# Update environment variable
export EMBEDDING_PROVIDER=ollama

# Restart services
docker compose restart embedding-processor processing-pipeline

# Or use the Ollama-specific compose file
docker compose -f docker-compose.yml up -d
```

## Monitoring and Maintenance

### Regular Maintenance

```bash
# Check disk usage
docker system df

# Clean up unused images
docker image prune

# Clean up unused volumes
docker volume prune

# Update HuggingFace models
docker compose exec embedding-processor python init_huggingface.py
```

### Performance Monitoring

```bash
# Check service metrics
curl http://localhost:8001/metrics
curl http://localhost:8003/metrics
curl http://localhost:8007/metrics

# Monitor resource usage
docker stats
```

## Security Considerations

### Model Security

- HuggingFace models are downloaded from trusted sources
- Models are cached locally for offline use
- No data is sent to external services during inference

### Network Security

- Services communicate over internal Docker network
- External access is limited to necessary ports
- Consider using reverse proxy for production deployments

## Support

### Getting Help

1. **Check Logs**: Use `docker compose logs` to check service logs
2. **Health Checks**: Use the health check endpoints
3. **Test Scripts**: Run the provided test scripts
4. **Documentation**: Refer to the README files in each service directory

### Useful Commands

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart embedding-processor

# View service status
docker compose ps

# Check service logs
docker compose logs -f embedding-processor

# Access service shell
docker compose exec embedding-processor bash
``` 