# Embedding Processor with Ollama

This service provides vector embedding generation using self-hosted Ollama models. It's designed to be easily integrated with external services like n8n, Flowise, and other automation platforms.

## Features

- **Self-hosted embeddings**: Uses Ollama for local embedding generation
- **Multiple models**: Support for various embedding models (nomic-embed-text, all-minilm, e5-series, etc.)
- **External integration**: RESTful API for easy integration with n8n, Flowise, and other services
- **Vector storage**: Automatic storage in Qdrant vector database
- **Model management**: Automatic model pulling and availability checking

## Quick Start

### 1. Start the Services

```bash
cd mep_ainabox/core
docker compose up -d ollama embedding-processor
```

### 2. Initialize Ollama Models

```bash
# Wait for Ollama to start, then run:
docker compose exec embedding-processor python init_ollama.py
```

### 3. Test the Service

```bash
# Health check
curl http://localhost:8007/health

# List available models
curl http://localhost:8007/models

# Generate a single embedding
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "model": "nomic-embed-text"}'
```

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status including Ollama and Qdrant connections.

### Generate Single Embedding
```
POST /embed
```
Generate embedding for a single text (ideal for external services).

**Request:**
```json
{
  "text": "Your text here",
  "model": "nomic-embed-text"  // optional, defaults to DEFAULT_EMBEDDING_MODEL
}
```

**Response:**
```json
{
  "text": "Your text here",
  "embedding": [0.1, 0.2, 0.3, ...],
  "dimensions": 768,
  "model_used": "nomic-embed-text"
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
  "model": "nomic-embed-text"  // optional
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
  "model": "nomic-embed-text",  // optional
  "limit": 10  // optional, defaults to 10
}
```

### List Available Models
```
GET /models
```
List all available embedding models in Ollama.

## Integration with External Services

### n8n Integration

1. **HTTP Request Node**:
   - Method: POST
   - URL: `http://localhost:8007/embed`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "text": "{{ $json.text }}",
     "model": "nomic-embed-text"
   }
   ```

2. **Use the embedding**:
   - The response contains the embedding vector
   - Use it for similarity search, clustering, or other AI tasks

### Flowise Integration

1. **HTTP Request Tool**:
   - URL: `http://localhost:8007/embed`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Body: JSON with text and optional model

2. **Custom Node**:
   - Create a custom node that calls the embedding service
   - Use the embeddings for document similarity or semantic search

### Python Integration

```python
import httpx
import asyncio

async def get_embedding(text: str, model: str = "nomic-embed-text"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8007/embed",
            json={"text": text, "model": model}
        )
        return response.json()["embedding"]

# Usage
embedding = await get_embedding("Hello world")
print(f"Embedding dimensions: {len(embedding)}")
```

## Available Models

### Recommended Models

| Model | Dimensions | Quality | Speed | Use Case |
|-------|------------|---------|-------|----------|
| `nomic-embed-text` | 768 | High | Medium | General purpose |
| `all-minilm` | 384 | Good | Fast | Quick embeddings |
| `all-mpnet-base-v2` | 768 | High | Medium | High quality |
| `e5-large-v2` | 1024 | Excellent | Slow | Best quality |
| `e5-base-v2` | 768 | Good | Medium | Balanced |
| `e5-small-v2` | 384 | Good | Fast | Quick embeddings |

### Adding New Models

1. **Pull a model to Ollama**:
   ```bash
   docker compose exec ollama ollama pull model-name
   ```

2. **Update model dimensions** (if needed):
   Edit the `model_dimensions` dictionary in `main.py`

3. **Test the model**:
   ```bash
   curl -X POST http://localhost:8007/embed \
     -H "Content-Type: application/json" \
     -d '{"text": "test", "model": "model-name"}'
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `ollama` | Ollama service hostname |
| `OLLAMA_PORT` | `11434` | Ollama service port |
| `DEFAULT_EMBEDDING_MODEL` | `nomic-embed-text` | Default embedding model |
| `QDRANT_HOST` | `qdrant` | Qdrant vector database host |
| `QDRANT_PORT` | `6333` | Qdrant vector database port |

### Docker Compose

The service is configured in `docker-compose.yml`:

```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama

embedding-processor:
  build:
    context: ./processors/embedding_processor
  ports:
    - "8007:8007"
  environment:
    - OLLAMA_HOST=ollama
    - OLLAMA_PORT=11434
    - DEFAULT_EMBEDDING_MODEL=nomic-embed-text
  depends_on:
    - ollama
```

## Troubleshooting

### Common Issues

1. **Ollama not accessible**:
   ```bash
   # Check if Ollama is running
   docker compose ps ollama
   
   # Check Ollama logs
   docker compose logs ollama
   ```

2. **Model not found**:
   ```bash
   # Pull the model manually
   docker compose exec ollama ollama pull nomic-embed-text
   ```

3. **High memory usage**:
   - Use smaller models like `all-minilm` or `e5-small-v2`
   - Increase Docker memory limits

4. **Slow embedding generation**:
   - Use faster models like `all-minilm`
   - Ensure sufficient CPU resources

### Logs

```bash
# View embedding processor logs
docker compose logs embedding-processor

# View Ollama logs
docker compose logs ollama

# Follow logs in real-time
docker compose logs -f embedding-processor
```

## Performance Tips

1. **Model Selection**:
   - Use `all-minilm` for speed-critical applications
   - Use `e5-large-v2` for quality-critical applications
   - Use `nomic-embed-text` for balanced performance

2. **Batch Processing**:
   - Process multiple texts in batches when possible
   - Use the `/process` endpoint for large documents

3. **Caching**:
   - Consider implementing embedding caching for repeated texts
   - Use Redis or similar for caching frequently used embeddings

## Security Considerations

1. **Network Access**:
   - The service is exposed on port 8007
   - Consider using reverse proxy with authentication
   - Restrict access to trusted networks

2. **Model Security**:
   - Only pull models from trusted sources
   - Regularly update Ollama and models
   - Monitor model usage and performance

## Development

### Local Development

```bash
# Start only required services
docker compose up -d ollama qdrant

# Run embedding processor locally
cd processors/embedding_processor
pip install -r requirements.txt
python main.py
```

### Testing

```bash
# Test the API
curl http://localhost:8007/health

# Test embedding generation
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
```

### Adding New Features

1. **New endpoints**: Add to `main.py`
2. **New models**: Update `model_dimensions` and test
3. **New integrations**: Create example scripts in this directory 