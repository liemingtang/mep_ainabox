# Embedding Processor with Ollama or HuggingFace

This service provides vector embedding generation using either self-hosted Ollama models or HuggingFace Transformers models. It's designed to be easily integrated with external services like n8n, Flowise, and other automation platforms.

## Features

- **Multiple embedding providers**: Choose between Ollama (self-hosted) or HuggingFace (cloud/local)
- **Multiple models**: Support for various embedding models from both providers
- **External integration**: RESTful API for easy integration with n8n, Flowise, and other services
- **Vector storage**: Automatic storage in Qdrant vector database
- **Model management**: Automatic model pulling and availability checking
- **Easy switching**: Simple configuration to switch between providers

## Quick Start

### Option 1: Using Ollama (Self-hosted)

```bash
cd mep_ainabox/core
docker compose up -d ollama embedding-processor
```

### Option 2: Using HuggingFace (Recommended for quick setup)

The system now uses the centralized HuggingFace embedding service located in `mep_ainabox/services/`.

```bash
cd mep_ainabox/services
docker compose up -d huggingface-embeddings
```

### Initialize Models

#### For Ollama:
```bash
# Wait for Ollama to start, then run:
docker compose exec embedding-processor python init_ollama.py
```

#### For HuggingFace:
The HuggingFace service automatically downloads and initializes models on first use.
No manual initialization is required.

### Test the Service

```bash
# Health check
curl http://localhost:8082/

# Generate a single embedding
curl -X POST http://localhost:8082/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["Hello world"]}'
```

## Provider Comparison

| Feature | Ollama | HuggingFace |
|---------|--------|-------------|
| **Privacy** | Complete (self-hosted) | Good (local models) |
| **Setup** | Requires Ollama server | Simple (direct download) |
| **Model Selection** | Limited | Extensive |
| **Resource Usage** | Higher | Lower |
| **Offline Capability** | Full | Limited (after download) |
| **Custom Models** | Supported | Supported |
| **GPU Support** | Yes | Yes |

### When to Use Each Provider

**Use Ollama when:**
- You need complete privacy and control
- Working in offline environments
- Using custom or specialized models
- Have sufficient server resources

**Use HuggingFace when:**
- You want quick setup and deployment
- Need access to a wide variety of models
- Working in development or testing environments
- Have limited server resources

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status including provider and Qdrant connections.

### Generate Single Embedding
```
POST /embed
```
Generate embedding for a single text (ideal for external services).

**Request:**
```json
{
  "text": "Your text here",
  "model": "sentence-transformers/all-MiniLM-L6-v2",  // optional
  "provider": "huggingface"  // optional, defaults to EMBEDDING_PROVIDER
}
```

**Response:**
```json
{
  "text": "Your text here",
  "embedding": [0.1, 0.2, 0.3, ...],
  "dimensions": 384,
  "model_used": "sentence-transformers/all-MiniLM-L6-v2",
  "provider_used": "huggingface"
}
```

### Process Document Embeddings
```
POST /process
```
Process a document with text chunking and store embeddings in Qdrant.

**Request:**
```json
{
  "document_id": "doc123",
  "text_content": "Long document text...",
  "metadata": {"source": "file.pdf", "author": "John Doe"},
  "model": "sentence-transformers/all-MiniLM-L6-v2",  // optional
  "provider": "huggingface"  // optional
}
```

### Search Similar Documents
```
POST /search
```
Search for similar documents using semantic similarity.

**Request:**
```json
{
  "text": "Search query",
  "model": "sentence-transformers/all-MiniLM-L6-v2",  // optional
  "provider": "huggingface",  // optional
  "limit": 10  // optional, defaults to 10
}
```

### List Available Models
```
GET /models
```
List all available embedding models for the current provider.

## Available Models

### HuggingFace Models (Recommended)

| Model | Dimensions | Quality | Speed | Use Case |
|-------|------------|---------|-------|----------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Good | Fast | General purpose |
| `sentence-transformers/paraphrase-MiniLM-L3-v2` | 384 | Good | Very Fast | Quick embeddings |
| `sentence-transformers/all-mpnet-base-v2` | 768 | High | Medium | High quality |
| `sentence-transformers/e5-small-v2` | 384 | Good | Fast | Balanced |
| `sentence-transformers/e5-base-v2` | 768 | Excellent | Medium | Best quality |
| `sentence-transformers/e5-large-v2` | 1024 | Excellent | Slow | Best quality |
| `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` | 384 | Good | Fast | QA applications |

### Ollama Models

| Model | Dimensions | Quality | Speed | Use Case |
|-------|------------|---------|-------|----------|
| `nomic-embed-text` | 768 | High | Medium | General purpose |
| `all-minilm` | 384 | Good | Fast | Quick embeddings |
| `all-mpnet-base-v2` | 768 | High | Medium | High quality |
| `e5-large-v2` | 1024 | Excellent | Slow | Best quality |
| `e5-base-v2` | 768 | Good | Medium | Balanced |
| `e5-small-v2` | 384 | Good | Fast | Quick embeddings |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `ollama` | Provider: "ollama" or "huggingface" |
| `OLLAMA_HOST` | `ollama` | Ollama service hostname |
| `OLLAMA_PORT` | `11434` | Ollama service port |
| `OLLAMA_DEFAULT_MODEL` | `nomic-embed-text` | Default Ollama model |
| `HF_DEFAULT_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Default HuggingFace model |
| `HF_CACHE_DIR` | `/app/cache/huggingface` | HuggingFace cache directory |
| `HF_DEVICE` | `cpu` | Device for HuggingFace models |
| `HF_BATCH_SIZE` | `32` | Batch size for HuggingFace processing |
| `QDRANT_HOST` | `qdrant` | Qdrant vector database host |
| `QDRANT_PORT` | `6333` | Qdrant vector database port |

### Docker Compose Configurations

#### For Ollama (Original)
```yaml
# docker-compose.yml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama

embedding-processor:
  build:
    context: ./processors/embedding_processor
  environment:
    - EMBEDDING_PROVIDER=ollama
    - OLLAMA_HOST=ollama
    - OLLAMA_PORT=11434
  depends_on:
    - ollama
```

#### For HuggingFace (New)
```yaml
# docker-compose.huggingface.yml
embedding-processor-hf:
  build:
    context: ./processors/embedding_processor
  environment:
    - EMBEDDING_PROVIDER=huggingface
    - HF_DEFAULT_MODEL=sentence-transformers/all-MiniLM-L6-v2
    - HF_CACHE_DIR=/app/cache/huggingface
  volumes:
    - huggingface_cache:/app/cache/huggingface
```

## Integration with External Services

### n8n Integration

1. **HTTP Request Node**:
   - Method: POST
   - URL: `http://localhost:8082/embed`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "inputs": ["{{ $json.text }}"]
   }
   ```

2. **Use the embedding**:
   - The response contains the embedding vector
   - Use it for similarity search, clustering, or other AI tasks

### Flowise Integration

1. **HTTP Request Tool**:
   - URL: `http://localhost:8082/embed`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Body: JSON with inputs array

2. **Custom Node**:
   - Create a custom node that calls the embedding service
   - Use the embeddings for document similarity or semantic search

### Python Integration

```python
import httpx
import asyncio

async def get_embedding(text: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8082/embed",
            json={
                "inputs": [text]
            }
        )
        return response.json()[0]

# Usage
embedding = await get_embedding("Hello world")
print(f"Embedding dimensions: {len(embedding)}")
```

## Performance Tips

### HuggingFace Optimization

1. **Model Selection**:
   - Use `paraphrase-MiniLM-L3-v2` for speed-critical applications
   - Use `all-mpnet-base-v2` for quality-critical applications
   - Use `all-MiniLM-L6-v2` for balanced performance

2. **Batch Processing**:
   - Increase `HF_BATCH_SIZE` for better throughput
   - Process multiple texts in batches when possible

3. **Caching**:
   - Models are automatically cached in `HF_CACHE_DIR`
   - Consider using persistent volumes for cache

### Ollama Optimization

1. **Model Selection**:
   - Use `all-minilm` for speed-critical applications
   - Use `e5-large-v2` for quality-critical applications
   - Use `nomic-embed-text` for balanced performance

2. **Resource Management**:
   - Ensure sufficient memory for Ollama
   - Use GPU acceleration if available

## Troubleshooting

### Common Issues

1. **HuggingFace model download fails**:
   ```bash
   # Check internet connection
   # Verify cache directory permissions
   cd mep_ainabox/services
   docker compose logs huggingface-embeddings
   ```

2. **Ollama not accessible**:
   ```bash
   # Check if Ollama is running
   docker compose ps ollama
   
   # Check Ollama logs
   docker compose logs ollama
   ```

3. **High memory usage**:
   - Use smaller models like `paraphrase-MiniLM-L3-v2` or `all-minilm`
   - Increase Docker memory limits
   - Reduce batch size for HuggingFace

4. **Slow embedding generation**:
   - Use faster models
   - Ensure sufficient CPU resources
   - Consider GPU acceleration

### Logs

```bash
# View embedding processor logs
docker compose logs embedding-processor
# or
docker compose -f docker-compose.huggingface.yml logs embedding-processor-hf

# View Ollama logs (if using Ollama)
docker compose logs ollama

# Follow logs in real-time
docker compose logs -f embedding-processor
```

## Security Considerations

1. **Network Access**:
   - The service is exposed on port 8082
   - Consider using reverse proxy with authentication
   - Restrict access to trusted networks

2. **Model Security**:
   - Only use models from trusted sources
   - Regularly update dependencies
   - Monitor model usage and performance

3. **Data Privacy**:
   - HuggingFace models are downloaded locally
   - No data is sent to external services during inference
   - Consider using Ollama for complete privacy

## Development

### Local Development

```bash
# Start only required services
docker compose up -d qdrant

# Run embedding processor locally
cd processors/embedding_processor
pip install -r requirements.txt
export EMBEDDING_PROVIDER=huggingface
python main.py
```

### Testing

```bash
# Test the API
curl http://localhost:8082/

# Test embedding generation
curl -X POST http://localhost:8082/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["test"]}'
```

### Adding New Features

1. **New endpoints**: Add to `main.py`
2. **New models**: Update model dimensions in `config.py`
3. **New integrations**: Create example scripts in this directory

## Migration Guide

### From Ollama to HuggingFace

1. **Stop Ollama services**:
   ```bash
   docker compose down ollama embedding-processor
   ```

2. **Start HuggingFace services**:
   ```bash
   docker compose -f docker-compose.huggingface.yml up -d
   ```

3. **Initialize HuggingFace models**:
   ```bash
   docker compose -f docker-compose.huggingface.yml exec embedding-processor-hf python init_huggingface.py
   ```

4. **Update environment variables**:
   ```bash
   export EMBEDDING_PROVIDER=huggingface
   ```

### From HuggingFace to Ollama

1. **Stop HuggingFace services**:
   ```bash
   docker compose -f docker-compose.huggingface.yml down
   ```

2. **Start Ollama services**:
   ```bash
   docker compose up -d ollama embedding-processor
   ```

3. **Initialize Ollama models**:
   ```bash
   docker compose exec embedding-processor python init_ollama.py
   ```

4. **Update environment variables**:
   ```bash
   export EMBEDDING_PROVIDER=ollama
   ``` 