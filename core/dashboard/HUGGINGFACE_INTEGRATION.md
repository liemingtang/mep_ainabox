# HuggingFace Embedding Service Integration

## Overview

The dashboard LLM search functionality has been updated to use the HuggingFace embedding service instead of the embedding processor service (port 8007). This change provides better performance and reliability for generating text embeddings.

## Changes Made

### 1. Backend API Changes (`main.py`)

**Modified Function**: `llm_search()` in `/api/llm-search` endpoint

**Key Changes**:
- **Before**: Used `http://localhost:8007/embed?text={query}&provider=huggingface`
- **After**: Uses `http://localhost:8082/embed` with JSON payload `{"inputs": [query]}`

**New Features**:
- Enhanced error handling with specific error messages
- Comprehensive logging for debugging
- Timeout configuration (30 seconds)
- Proper response parsing for HuggingFace service format

### 2. Environment Configuration

**Added Environment Variable**:
```bash
HUGGINGFACE_EMBEDDING_URL=http://localhost:8082
```

**Updated Files**:
- `main.py` - Added environment variable definition
- `start_dashboard_host.sh` - Added export statement
- `start_dashboard.sh` - Added export statement
- `config/dashboard_config.json` - Added service endpoint configuration

### 3. Frontend Updates (`search.html`)

**UI Changes**:
- Updated page description to mention HuggingFace embeddings
- Enhanced welcome message to highlight semantic similarity search
- Improved user experience messaging

### 4. Error Handling

**New Error Types Handled**:
- Connection errors to HuggingFace service
- Timeout exceptions
- HTTP status errors
- Invalid response format errors

**User-Friendly Error Messages**:
- Clear indication when HuggingFace service is unavailable
- Specific error codes and descriptions
- Guidance for troubleshooting

## API Integration Details

### HuggingFace Service API

**Endpoint**: `POST http://localhost:8082/embed`

**Request Format**:
```json
{
  "inputs": ["Your text query here"]
}
```

**Response Format**:
```json
[
  [0.123, 0.456, 0.789, ...]  // 384-dimensional embedding vector
]
```

### Integration Flow

1. **Query Reception**: User submits search query
2. **Embedding Generation**: Call HuggingFace service with query text
3. **Vector Search**: Use generated embedding to search Qdrant database
4. **LLM Processing**: Send context to DeepSeek API for intelligent response
5. **Result Delivery**: Return both LLM response and source documents

## Testing

### Test Script

A comprehensive test script has been created: `test_huggingface_integration.py`

**Usage**:
```bash
cd mep_ainabox/core/dashboard
python3 test_huggingface_integration.py
```

**What it tests**:
- HuggingFace service health check
- Embedding generation functionality
- Qdrant vector search integration
- Complete workflow validation

### Manual Testing

1. **Start Services**:
   ```bash
   cd mep_ainabox/services
   docker compose up -d huggingface-embeddings qdrant
   ```

2. **Start Dashboard**:
   ```bash
   cd mep_ainabox/core
   ./start_dashboard_host.sh
   ```

3. **Access LLM Search**:
   - Navigate to: `http://localhost:8010/llm-search`
   - Submit a test query
   - Verify results are returned

## Configuration

### Required Services

1. **HuggingFace Embedding Service** (`http://localhost:8082`)
   - Container: `mep-huggingface-embeddings`
   - Model: `sentence-transformers/all-MiniLM-L6-v2`
   - Port: 8082

2. **Qdrant Vector Database** (`http://localhost:6333`)
   - Container: `mep-qdrant`
   - Collection: `documents`
   - Port: 6333

### Environment Variables

```bash
# Required
HUGGINGFACE_EMBEDDING_URL=http://localhost:8082
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=qdrant_api_key

# Optional (for LLM responses)
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
```

## Troubleshooting

### Common Issues

1. **HuggingFace Service Not Available**
   ```
   Error: Failed to connect to HuggingFace embedding service
   Solution: Ensure huggingface-embeddings container is running
   ```

2. **Timeout Errors**
   ```
   Error: Timeout while generating embedding
   Solution: Check service health and increase timeout if needed
   ```

3. **Invalid Response Format**
   ```
   Error: Failed to generate embedding - no valid data returned
   Solution: Verify HuggingFace service is properly configured
   ```

### Health Checks

```bash
# Check HuggingFace service
curl http://localhost:8082/

# Check Qdrant service
curl http://localhost:6333/collections

# Run integration test
python3 test_huggingface_integration.py
```

## Performance Benefits

### Advantages of HuggingFace Service

1. **Dedicated Service**: Optimized specifically for embedding generation
2. **Better Performance**: ONNX optimization and batch processing
3. **Reliability**: Containerized service with health checks
4. **Scalability**: Configurable batch sizes and resource limits
5. **Consistency**: Same model across all embedding operations

### Expected Improvements

- **Faster Response Times**: Dedicated embedding service
- **Better Reliability**: Reduced dependency on processing pipeline
- **Enhanced Error Handling**: More specific error messages
- **Improved Debugging**: Comprehensive logging

## Migration Notes

### Backward Compatibility

- The change is transparent to end users
- No changes required to existing document processing
- Qdrant database structure remains unchanged
- API response format is identical

### Rollback Procedure

If needed, the system can be rolled back by:
1. Reverting the `main.py` changes
2. Removing the `HUGGINGFACE_EMBEDDING_URL` environment variable
3. Restarting the dashboard service

## Future Enhancements

### Potential Improvements

1. **Model Selection**: Allow different embedding models
2. **Batch Processing**: Support multiple queries in single request
3. **Caching**: Implement embedding result caching
4. **Metrics**: Add performance monitoring and metrics
5. **Fallback**: Implement fallback to other embedding services
