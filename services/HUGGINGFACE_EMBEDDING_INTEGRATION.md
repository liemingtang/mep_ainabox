# HuggingFace Embedding Service Integration

## Overview

The HuggingFace Text Embeddings Inference Service has been integrated into the mep_ainabox system to provide high-quality text embeddings for document processing and vector search capabilities.

## Service Details

- **Service Name**: `huggingface-embeddings`
- **Container Name**: `mep-huggingface-embeddings`
- **Port**: `8082` (mapped from container port 80)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Batch Limits**: 
  - Max client batch size: 200 items
  - Max batch requests: 50 concurrent

## Quick Start

### Start Embedding Service Only
```bash
./start_embedding_service.sh start
```

### Start All Services
```bash
./start_embedding_service.sh all
```

### Check Status
```bash
./start_embedding_service.sh status
```

### View Logs
```bash
./start_embedding_service.sh logs
```

## API Usage

### Health Check
```bash
curl http://localhost:8082/
```

### Generate Embeddings
```bash
curl -X POST http://localhost:8082/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["Your text here"]}'
```

### Batch Processing
```bash
curl -X POST http://localhost:8082/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["Text 1", "Text 2", "Text 3"]}'
```

## Integration with Other Services

### Qdrant Vector Database
The embedding service works seamlessly with the Qdrant vector database:
- Generate embeddings using this service
- Store vectors in Qdrant for similarity search
- Use the same network for container-to-container communication

### Document Processing Pipeline
- Text extraction → Embedding generation → Vector storage
- Batch processing for large document sets
- Real-time embedding generation for new documents

## Configuration

### Environment Variables
- `MODEL_ID`: The HuggingFace model to use (default: sentence-transformers/all-MiniLM-L6-v2)

### Volume Mounts
- `huggingface_cache:/data`: Persistent cache for model files

### Network
- Connected to `mep-services-network` for service communication

## Performance Tuning

### Batch Size Optimization
- **Small batches (1-50)**: Good for real-time processing
- **Medium batches (50-150)**: Balanced performance and memory
- **Large batches (150-200)**: Maximum throughput for bulk processing

### Memory Considerations
- CPU-only model for resource efficiency
- ONNX optimization for faster inference
- Configurable batch limits to prevent memory issues

## Troubleshooting

### Common Issues

1. **413 Payload Too Large**
   - Reduce batch size in your requests
   - Current limit: 200 items per batch

2. **Service Unavailable**
   - Check container status: `docker compose ps huggingface-embeddings`
   - View logs: `./start_embedding_service.sh logs`

3. **Model Download Issues**
   - Check internet connectivity
   - Verify HuggingFace model availability
   - Clear cache volume if needed

### Health Checks
The service includes built-in health checks:
- HTTP endpoint verification
- Automatic restart on failure
- 30-second check intervals

## Monitoring

### Logs
```bash
# View real-time logs
./start_embedding_service.sh logs

# View specific service logs
docker compose logs huggingface-embeddings
```

### Metrics
- Request processing times
- Batch size statistics
- Error rates and types

## Security Considerations

- No authentication required (internal service)
- Exposed on localhost only
- Containerized execution
- Network isolation via Docker networks

## Future Enhancements

- GPU acceleration support
- Multiple model support
- Authentication and API keys
- Load balancing for high availability
- Custom model fine-tuning capabilities
