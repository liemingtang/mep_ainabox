# Elasticsearch Integration in Queue Worker

The `process_file_processing_queue.py` script has been enhanced with Elasticsearch integration to store and index processed documents and their content.

## Overview

The queue worker now automatically:
- **Indexes document metadata** in the `documents` index
- **Stores document content** in the `document_content` index
- **Tracks processing statistics** and results
- **Handles errors gracefully** with optional Elasticsearch storage

## Features

### 1. Document Metadata Indexing
Each processed file is indexed in the `documents` index with:
- File information (name, path, size, type, checksum)
- Processing details (processor type, priority, status)
- Processing results and statistics
- Timestamps (created, modified, processed)
- Metadata and custom fields

### 2. Document Content Storage
Extracted text content is stored in the `document_content` index with:
- Full text content
- Content statistics (length, word count, line count)
- Processing statistics
- Document references and metadata

### 3. Processing Statistics
Comprehensive statistics are generated and stored:
- Content analysis (length, words, lines)
- Processing success/failure status
- Processing time and return codes
- Output size and performance metrics

### 4. Error Handling
- Graceful handling of Elasticsearch unavailability
- Error information stored in Elasticsearch when processing fails
- Detailed logging for troubleshooting

## Configuration

The Elasticsearch connection is configured in `config/main.yaml`:

```yaml
core:
  storage:
    elasticsearch:
      host: "localhost"
      port: 9200
      index_prefix: "documents"
      username: "elastic"
      password: "elastic_password"
      timeout: 30
```

## Data Structure

### Documents Index (`documents`)
```json
{
  "document_id": "12345",
  "queue_id": 67890,
  "filename": "example.txt",
  "file_path": "/path/to/example.txt",
  "parent_directory": "/path/to",
  "file_size": 1024,
  "file_type": ".txt",
  "mime_type": "text/plain",
  "checksum": "abc123def456",
  "processor_type": "text_processor",
  "priority": 5,
  "status": "completed",
  "processing_result": {
    "success": true,
    "processing_stats": {
      "content_length": 500,
      "word_count": 50,
      "line_count": 10,
      "processing_success": true
    },
    "output_size": 1000
  },
  "created_time": "2024-01-01T12:00:00",
  "modified_time": "2024-01-01T12:00:00",
  "processed_at": "2024-01-01T12:05:00",
  "metadata": {}
}
```

### Document Content Index (`document_content`)
```json
{
  "document_id": "12345",
  "queue_id": 67890,
  "filename": "example.txt",
  "text_content": "This is the extracted text content...",
  "content_length": 500,
  "processing_stats": {
    "content_length": 500,
    "word_count": 50,
    "line_count": 10,
    "processing_success": true,
    "processing_time": "2024-01-01T12:05:00",
    "return_code": 0
  },
  "created_at": "2024-01-01T12:05:00",
  "metadata": {}
}
```

## Usage

### Basic Processing
```bash
# Process files and automatically index in Elasticsearch
./batch_process_file_queue.sh --limit 10
```

### Processing with Specific Processor
```bash
# Process text files and index results
./batch_process_file_queue.sh --processor-type text_processor --limit 5
```

### Continuous Processing
```bash
# Process continuously and index all results
./batch_process_file_queue.sh --script-args --continuous --interval 30
```

## Elasticsearch Queries

### Search for Documents
```bash
# Search by filename
curl -X GET "localhost:9200/documents/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "match": {
      "filename": "example.txt"
    }
  }
}'

# Search by content
curl -X GET "localhost:9200/document_content/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "match": {
      "text_content": "search term"
    }
  }
}'

# Search by processing status
curl -X GET "localhost:9200/documents/_search" -H "Content-Type: application/json" -d'
{
  "query": {
    "term": {
      "status": "completed"
    }
  }
}'
```

### Get Processing Statistics
```bash
# Get document count by status
curl -X GET "localhost:9200/documents/_search" -H "Content-Type: application/json" -d'
{
  "size": 0,
  "aggs": {
    "status_counts": {
      "terms": {
        "field": "status"
      }
    }
  }
}'

# Get average processing stats
curl -X GET "localhost:9200/documents/_search" -H "Content-Type: application/json" -d'
{
  "size": 0,
  "aggs": {
    "avg_content_length": {
      "avg": {
        "field": "processing_result.processing_stats.content_length"
      }
    }
  }
}'
```

## Testing

### Run Elasticsearch Tests
```bash
# Test Elasticsearch functionality
python3 test_elasticsearch.py
```

### Test in Docker
```bash
# Test in Docker container
docker run --rm --network host \
  -v /path/to/config:/app/config \
  mep-folder-scanner:latest \
  python3 /app/test_elasticsearch.py
```

## Monitoring

### Check Elasticsearch Health
```bash
# Check cluster health
curl -X GET "localhost:9200/_cluster/health"

# Check indices
curl -X GET "localhost:9200/_cat/indices?v"

# Check document counts
curl -X GET "localhost:9200/_cat/count/documents?v"
curl -X GET "localhost:9200/_cat/count/document_content?v"
```

### Monitor Processing
```bash
# Get recent documents
curl -X GET "localhost:9200/documents/_search" -H "Content-Type: application/json" -d'
{
  "sort": [
    {
      "processed_at": {
        "order": "desc"
      }
    }
  ],
  "size": 10
}'
```

## Error Handling

### Elasticsearch Unavailable
If Elasticsearch is not available:
- Processing continues normally
- Warning messages are logged
- No data is lost (PostgreSQL still works)
- Processing results are still valid

### Connection Issues
- Automatic retry with exponential backoff
- Graceful degradation
- Detailed error logging
- No impact on file processing

## Performance Considerations

### Indexing Performance
- Bulk indexing for large batches
- Async operations for better performance
- Connection pooling
- Timeout handling

### Storage Optimization
- Content length limits
- Metadata size limits
- Index lifecycle management
- Regular cleanup of old data

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if Elasticsearch is running
   curl -X GET "localhost:9200/_cluster/health"
   ```

2. **Authentication Failed**
   ```bash
   # Check credentials in config
   cat config/main.yaml | grep elasticsearch
   ```

3. **Index Not Found**
   ```bash
   # Create index if needed
   curl -X PUT "localhost:9200/documents"
   curl -X PUT "localhost:9200/document_content"
   ```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
./batch_process_file_queue.sh --limit 1
```

## Integration with Other Services

### Dashboard Integration
The dashboard can now display:
- Document processing statistics
- Content search capabilities
- Processing performance metrics
- Error rates and trends

### API Integration
Other services can query Elasticsearch for:
- Document search and retrieval
- Content analysis
- Processing statistics
- Performance monitoring

## Future Enhancements

### Planned Features
- **Full-text search** across all documents
- **Content similarity** analysis
- **Processing pipeline** tracking
- **Real-time monitoring** dashboard
- **Advanced analytics** and reporting

### Performance Optimizations
- **Bulk indexing** for large datasets
- **Index optimization** and management
- **Caching** for frequently accessed data
- **Compression** for large content fields 