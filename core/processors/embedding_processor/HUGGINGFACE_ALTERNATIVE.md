# HuggingFace Alternative for Embeddings Processing

## Overview

The embedding processor now supports two providers for generating vector embeddings:

1. **Ollama** (original) - Self-hosted models with complete privacy
2. **HuggingFace** (new) - Local HuggingFace Transformers models with easy setup

## Key Features

### ✅ What's New

- **Dual Provider Support**: Choose between Ollama and HuggingFace
- **Easy Configuration**: Simple environment variable to switch providers
- **Wide Model Selection**: Access to hundreds of HuggingFace models
- **Automatic Model Management**: Models are downloaded and cached automatically
- **Backward Compatibility**: Existing Ollama setup continues to work unchanged

### 🔧 Configuration

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `ollama` | Provider: "ollama" or "huggingface" |
| `HF_DEFAULT_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Default HuggingFace model |
| `HF_CACHE_DIR` | `/app/cache/huggingface` | Cache directory for models |
| `HF_DEVICE` | `cpu` | Device (cpu/cuda) |
| `HF_BATCH_SIZE` | `32` | Batch size for processing |

#### Quick Setup

**For HuggingFace:**
```bash
# Set provider
export EMBEDDING_PROVIDER=huggingface

# Start service
docker compose -f docker-compose.huggingface.yml up -d

# Initialize models
docker compose -f docker-compose.huggingface.yml exec embedding-processor-hf python init_huggingface.py
```

**For Ollama (existing):**
```bash
# Set provider (default)
export EMBEDDING_PROVIDER=ollama

# Start service
docker compose up -d ollama embedding-processor

# Initialize models
docker compose exec embedding-processor python init_ollama.py
```

## API Usage

### Single Embedding

```bash
# HuggingFace
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "provider": "huggingface"
  }'

# Ollama
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "model": "nomic-embed-text",
    "provider": "ollama"
  }'
```

### Document Processing

```bash
curl -X POST http://localhost:8007/process \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc123",
    "text_content": "Your document text...",
    "metadata": {"source": "file.pdf"},
    "provider": "huggingface"
  }'
```

### Similarity Search

```bash
curl -X POST http://localhost:8007/search \
  -H "Content-Type: application/json" \
  -d '{
    "text": "search query",
    "limit": 10,
    "provider": "huggingface"
  }'
```

## Available Models

### HuggingFace Models

| Model | Dimensions | Quality | Speed | Use Case |
|-------|------------|---------|-------|----------|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Good | Fast | General purpose |
| `sentence-transformers/paraphrase-MiniLM-L3-v2` | 384 | Good | Very Fast | Quick embeddings |
| `sentence-transformers/all-mpnet-base-v2` | 768 | High | Medium | High quality |
| `sentence-transformers/e5-small-v2` | 384 | Good | Fast | Balanced |
| `sentence-transformers/e5-base-v2` | 768 | Excellent | Medium | Best quality |
| `sentence-transformers/e5-large-v2` | 1024 | Excellent | Slow | Best quality |

### Ollama Models (Existing)

| Model | Dimensions | Quality | Speed | Use Case |
|-------|------------|---------|-------|----------|
| `nomic-embed-text` | 768 | High | Medium | General purpose |
| `all-minilm` | 384 | Good | Fast | Quick embeddings |
| `e5-large-v2` | 1024 | Excellent | Slow | Best quality |

## Provider Comparison

| Feature | Ollama | HuggingFace |
|---------|--------|-------------|
| **Setup Complexity** | Medium (requires Ollama server) | Low (direct download) |
| **Model Selection** | Limited | Extensive (hundreds of models) |
| **Resource Usage** | Higher | Lower |
| **Privacy** | Complete (self-hosted) | Good (local models) |
| **Offline Capability** | Full | Limited (after download) |
| **Custom Models** | Supported | Supported |
| **GPU Support** | Yes | Yes |

## Migration Guide

### From Ollama to HuggingFace

1. **Stop Ollama services:**
   ```bash
   docker compose down ollama embedding-processor
   ```

2. **Start HuggingFace services:**
   ```bash
   docker compose -f docker-compose.huggingface.yml up -d
   ```

3. **Initialize HuggingFace models:**
   ```bash
   docker compose -f docker-compose.huggingface.yml exec embedding-processor-hf python init_huggingface.py
   ```

4. **Update your API calls:**
   ```python
   # Add provider parameter
   response = await client.post("/embed", json={
       "text": "Hello world",
       "provider": "huggingface"
   })
   ```

### From HuggingFace to Ollama

1. **Stop HuggingFace services:**
   ```bash
   docker compose -f docker-compose.huggingface.yml down
   ```

2. **Start Ollama services:**
   ```bash
   docker compose up -d ollama embedding-processor
   ```

3. **Initialize Ollama models:**
   ```bash
   docker compose exec embedding-processor python init_ollama.py
   ```

## Testing

Run the comprehensive test suite:

```bash
# Test both providers
python test_embeddings.py

# Test specific provider
curl -X POST http://localhost:8007/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test", "provider": "huggingface"}'
```

## Performance Tips

### HuggingFace Optimization

1. **Model Selection:**
   - Use `paraphrase-MiniLM-L3-v2` for speed
   - Use `all-mpnet-base-v2` for quality
   - Use `all-MiniLM-L6-v2` for balance

2. **Batch Processing:**
   - Increase `HF_BATCH_SIZE` for throughput
   - Process multiple texts together

3. **Caching:**
   - Models are cached in `HF_CACHE_DIR`
   - Use persistent volumes for cache

### Ollama Optimization

1. **Model Selection:**
   - Use `all-minilm` for speed
   - Use `e5-large-v2` for quality
   - Use `nomic-embed-text` for balance

2. **Resource Management:**
   - Ensure sufficient memory
   - Use GPU acceleration if available

## Troubleshooting

### Common Issues

1. **HuggingFace model download fails:**
   - Check internet connection
   - Verify cache directory permissions
   - Check available disk space

2. **Memory issues:**
   - Use smaller models
   - Reduce batch size
   - Increase Docker memory limits

3. **Slow performance:**
   - Use faster models
   - Enable GPU acceleration
   - Optimize batch size

### Logs

```bash
# HuggingFace logs
docker compose -f docker-compose.huggingface.yml logs embedding-processor-hf

# Ollama logs
docker compose logs ollama embedding-processor

# Follow logs
docker compose -f docker-compose.huggingface.yml logs -f embedding-processor-hf
```

## Benefits of HuggingFace Alternative

### ✅ Advantages

1. **Easy Setup**: No need for Ollama server
2. **Wide Model Selection**: Access to hundreds of models
3. **Lower Resource Usage**: More efficient than Ollama
4. **Active Community**: Regular updates and improvements
5. **Flexible Configuration**: Easy to customize

### ⚠️ Considerations

1. **Initial Download**: Models need to be downloaded first
2. **Internet Dependency**: Requires internet for initial setup
3. **Model Size**: Some models can be large
4. **Privacy**: Models are downloaded from HuggingFace

## Next Steps

1. **Try HuggingFace**: Start with the quick setup
2. **Test Performance**: Compare with your current Ollama setup
3. **Choose Provider**: Select based on your requirements
4. **Optimize**: Fine-tune configuration for your use case

## Support

- **Documentation**: See `README.md` for detailed documentation
- **Configuration**: See `config.py` for provider settings
- **Testing**: Use `test_embeddings.py` for validation
- **Examples**: Check the README for usage examples 