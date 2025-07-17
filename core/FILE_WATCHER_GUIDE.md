# File Watcher Service Guide

## Overview

The File Watcher service automatically monitors the `watch_folder` for new files and processes them through the MDIS pipeline. It's a fully functional component that integrates with the Core Processor to provide seamless document processing.

## Quick Start

### 1. Start the File Watcher
```bash
# Start the service
curl -X POST http://localhost:8009/api/v1/watch/start

# Check status
curl http://localhost:8009/api/v1/watch/status
```

### 2. Add Files for Processing
```bash
# Copy files to the watch folder
cp document.pdf ./watch_folder/
cp report.docx ./watch_folder/
cp data.csv ./watch_folder/
```

### 3. Monitor Processing
```bash
# Check processed files
curl http://localhost:8009/api/v1/watch/processed

# Check error files
curl http://localhost:8009/api/v1/watch/errors
```

## API Reference

### Health Check
```bash
GET /health
```
Returns service health status.

### Service Information
```bash
GET /
```
Returns service information including supported file types and current status.

### Start Watching
```bash
POST /api/v1/watch/start
```
Starts the file watcher. Returns:
```json
{
  "status": "started",
  "message": "File watcher started"
}
```

### Stop Watching
```bash
POST /api/v1/watch/stop
```
Stops the file watcher. Returns:
```json
{
  "status": "stopped",
  "message": "File watcher stopped"
}
```

### Get Status
```bash
GET /api/v1/watch/status
```
Returns current watcher status:
```json
{
  "status": "running",
  "watch_paths": "./watch_folder",
  "is_alive": true,
  "processed_files_count": 5,
  "error_files_count": 1,
  "last_activity": "2024-01-15T10:30:00",
  "currently_processing": 0
}
```

### List Processed Files
```bash
GET /api/v1/watch/processed
```
Returns list of successfully processed files:
```json
{
  "processed_files": [
    {
      "file_path": "./watch_folder/document.pdf",
      "processed_at": "2024-01-15T10:30:00",
      "document_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  ],
  "count": 1
}
```

### List Error Files
```bash
GET /api/v1/watch/errors
```
Returns list of files that failed processing:
```json
{
  "error_files": [
    {
      "file_path": "./watch_folder/invalid.xyz",
      "error_at": "2024-01-15T10:30:00",
      "error": "Invalid file type or size"
    }
  ],
  "count": 1
}
```

### Clear History
```bash
POST /api/v1/watch/clear-history
```
Clears processing history. Returns:
```json
{
  "status": "cleared",
  "message": "Processing history cleared"
}
```

### Manual File Processing
```bash
POST /api/v1/watch/process-file?file_path=/path/to/file.pdf
```
Manually process a specific file. Returns:
```json
{
  "status": "processing",
  "message": "File /path/to/file.pdf sent for processing"
}
```

## Supported File Types

### Documents
- **PDF**: `.pdf` - Portable Document Format
- **Word**: `.docx`, `.doc` - Microsoft Word documents

### Text Files
- **Plain Text**: `.txt` - Plain text files
- **HTML**: `.html`, `.htm` - Web pages and HTML documents

### Images
- **PNG**: `.png` - Portable Network Graphics
- **JPEG**: `.jpg`, `.jpeg` - Joint Photographic Experts Group
- **GIF**: `.gif` - Graphics Interchange Format
- **BMP**: `.bmp` - Bitmap images
- **TIFF**: `.tiff` - Tagged Image File Format

### Data Files
- **CSV**: `.csv` - Comma-separated values
- **Excel**: `.xlsx`, `.xls` - Microsoft Excel spreadsheets

## File Processing Flow

### 1. File Detection
- File watcher monitors the `watch_folder` directory
- Detects new files and file movements
- Triggers processing for each detected file

### 2. File Validation
- Checks file extension against supported types
- Validates file size (maximum 100MB)
- Rejects invalid files and moves them to error folder

### 3. Metadata Creation
- Generates SHA256 file hash
- Detects MIME type
- Creates document metadata with:
  - Filename and path
  - File size and type
  - Source information
  - Timestamp

### 4. Processing
- Sends metadata to Core Processor via API
- Waits for processing response
- Handles success and error cases

### 5. File Organization
- **Success**: Moves file to `processed/` folder
- **Error**: Moves file to `error/` folder
- Handles duplicate filenames with numbering

### 6. Status Update
- Updates processing history
- Records timestamps and document IDs
- Maintains real-time status information

## Configuration

### Environment Variables
```bash
# Core processor URL
CORE_PROCESSOR_URL=http://core-processor:8001

# Watch folder path
WATCH_PATHS=./watch_folder

# Processed files folder
PROCESSED_FOLDER=./processed

# Error files folder
ERROR_FOLDER=./error
```

### Docker Configuration
The file watcher is configured in `docker-compose.yml`:
```yaml
file-watcher:
  environment:
    - CORE_PROCESSOR_URL=http://core-processor:8001
    - WATCH_PATHS=/app/watch_folder
    - PROCESSED_FOLDER=/app/processed
    - ERROR_FOLDER=/app/error
  volumes:
    - ./watch_folder:/app/watch_folder:rw
    - ./processed:/app/processed:rw
    - ./error:/app/error:rw
```

## Testing

### Automated Tests
```bash
# Run comprehensive tests
python test_file_watcher.py
```

### Interactive Demo
```bash
# Run interactive demonstration
python demo_file_watcher.py
```

### Manual Testing
```bash
# 1. Start the file watcher
curl -X POST http://localhost:8009/api/v1/watch/start

# 2. Create a test file
echo "Test content" > ./watch_folder/test.txt

# 3. Wait for processing (1-2 seconds)
sleep 2

# 4. Check results
curl http://localhost:8009/api/v1/watch/processed
curl http://localhost:8009/api/v1/watch/errors

# 5. Stop the file watcher
curl -X POST http://localhost:8009/api/v1/watch/stop
```

## Troubleshooting

### Common Issues

#### File Watcher Not Starting
```bash
# Check if service is running
curl http://localhost:8009/health

# Check logs
docker-compose logs file-watcher
```

#### Files Not Being Processed
1. Check if file watcher is running:
   ```bash
   curl http://localhost:8009/api/v1/watch/status
   ```

2. Verify file type is supported:
   ```bash
   curl http://localhost:8009/ | jq '.supported_extensions'
   ```

3. Check file size (max 100MB):
   ```bash
   ls -lh ./watch_folder/
   ```

#### Processing Errors
1. Check error files:
   ```bash
   curl http://localhost:8009/api/v1/watch/errors
   ```

2. Check core processor health:
   ```bash
   curl http://localhost:8001/health
   ```

3. Check logs:
   ```bash
   docker-compose logs core-processor
   docker-compose logs file-watcher
   ```

### Error Messages

#### "Invalid file type or size"
- File extension not in supported list
- File size exceeds 100MB limit
- File is empty (0 bytes)

#### "Processing failed"
- Core processor is not available
- Network connectivity issues
- Database connection problems

#### "File no longer exists"
- File was moved or deleted before processing
- File system permissions issues

## Best Practices

### File Organization
- Use descriptive filenames
- Avoid special characters in filenames
- Keep files under 100MB for optimal processing

### Monitoring
- Regularly check processing status
- Monitor error files for issues
- Clear history periodically to manage memory usage

### Performance
- The file watcher processes files asynchronously
- Multiple files can be processed simultaneously
- Processing time depends on file size and type

### Security
- Only place trusted files in the watch folder
- Monitor processed files for sensitive content
- Use appropriate file permissions

## Integration Examples

### Python Integration
```python
import httpx
import asyncio

async def process_file(file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8009/api/v1/watch/process-file",
            params={"file_path": file_path}
        )
        return response.json()

# Usage
result = asyncio.run(process_file("/path/to/document.pdf"))
print(result)
```

### Shell Script Integration
```bash
#!/bin/bash

# Start file watcher
curl -X POST http://localhost:8009/api/v1/watch/start

# Process multiple files
for file in /path/to/documents/*.pdf; do
    cp "$file" ./watch_folder/
    echo "Added $file for processing"
done

# Wait for processing
sleep 10

# Check results
curl http://localhost:8009/api/v1/watch/processed | jq '.count'
```

### Cron Job Integration
```bash
# Add to crontab to process files every hour
0 * * * * /usr/bin/curl -X POST http://localhost:8009/api/v1/watch/start
```

## Advanced Features

### Custom File Types
To add support for new file types, modify the `SUPPORTED_EXTENSIONS` dictionary in `main.py`:
```python
SUPPORTED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    # Add new types here
    '.md': 'text/markdown',
    '.json': 'application/json',
}
```

### Multiple Watch Folders
Configure multiple watch paths by setting the `WATCH_PATHS` environment variable:
```bash
WATCH_PATHS=/app/watch_folder1,/app/watch_folder2
```

### Custom Processing Logic
Extend the `DocumentHandler` class to add custom processing logic:
```python
class CustomDocumentHandler(DocumentHandler):
    async def process_document(self, file_path: str):
        # Add custom preprocessing
        await self.preprocess_file(file_path)
        
        # Call parent processing
        await super().process_document(file_path)
        
        # Add custom postprocessing
        await self.postprocess_file(file_path)
```

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs file-watcher`
3. Verify configuration and environment variables
4. Test with the provided test scripts 