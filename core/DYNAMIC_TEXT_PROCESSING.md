# Dynamic Text Processing

This document describes the dynamic text processing system that allows you to extract text from any folder on your system without modifying Docker Compose configurations.

## Overview

The dynamic text processing system consists of two main components:

1. **`text_processor_dynamic.sh`** - Bash script that creates temporary Docker containers
2. **`text_processor.py`** - Python script that runs inside the container to extract text

Both components work together to provide flexible, on-demand text extraction from any folder.

## Features

- ✅ **Dynamic Mounting**: Mount any folder without Docker Compose changes
- ✅ **Read-Only Access**: Folders are mounted read-only for security
- ✅ **Temporary Containers**: Auto-cleanup after use
- ✅ **Multiple File Types**: Supports txt, md, csv, json, xml, html, source code, etc.
- ✅ **Encoding Support**: Handles UTF-8, latin-1, cp1252, iso-8859-1
- ✅ **Concurrent Processing**: Process multiple files simultaneously
- ✅ **Recursive Scanning**: Option to scan subdirectories
- ✅ **Multiple Output Formats**: JSON, text, or summary reports
- ✅ **Quality Metrics**: Text length and quality scores

## Quick Start

### Basic Usage

```bash
# Extract text from any folder
./core/text_processor_dynamic.sh /path/to/folder

# Preview what would be processed (dry run)
./core/text_processor_dynamic.sh /path/to/folder --dry-run

# Process with custom settings
./core/text_processor_dynamic.sh /path/to/folder --max-depth 2 --concurrent 10 --output summary
```

### Examples

```bash
# Process external drive
./core/text_processor_dynamic.sh /media/user/USB_DRIVE/documents

# Process network share
./core/text_processor_dynamic.sh /mnt/network_share/projects

# Process current directory (max depth 1)
./core/text_processor_dynamic.sh . --max-depth 1 --output text

# High-performance processing
./core/text_processor_dynamic.sh /large/document/folder --concurrent 20 --no-recursive
```

## Command Line Options

### `text_processor_dynamic.sh`

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run, -d` | Show what would be processed without actually doing it | `false` |
| `--recursive, -r` | Process subdirectories recursively | `true` |
| `--no-recursive` | Don't process subdirectories | - |
| `--max-depth <depth>` | Maximum directory depth to scan | unlimited |
| `--concurrent <num>` | Number of concurrent processing jobs | `5` |
| `--output <format>` | Output format: json, text, summary | `json` |
| `--pipeline-url <url>` | Processing pipeline URL | `http://localhost:8003` |
| `--help, -h` | Show help message | - |

### `text_processor.py`

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Show what would be processed without actually doing it | `false` |
| `--recursive` | Process subdirectories recursively | `true` |
| `--no-recursive` | Don't process subdirectories | - |
| `--max-depth <depth>` | Maximum directory depth to scan | unlimited |
| `--concurrent <num>` | Number of concurrent processing jobs | `5` |
| `--output <format>` | Output format: json, text, summary | `json` |

## Supported File Types

The text processor supports a wide range of file types:

### Text Files
- `.txt` - Plain text files
- `.md` - Markdown files
- `.csv` - Comma-separated values
- `.json` - JSON files
- `.xml` - XML files
- `.html`, `.htm` - HTML files

### Source Code
- `.py` - Python files
- `.js` - JavaScript files
- `.java` - Java files
- `.cpp`, `.c`, `.h` - C/C++ files
- `.php` - PHP files
- `.rb` - Ruby files
- `.go` - Go files
- `.rs` - Rust files
- `.swift` - Swift files
- `.kt` - Kotlin files

### Configuration & Logs
- `.log`, `.out`, `.err` - Log files
- `.conf`, `.cfg`, `.ini` - Configuration files
- `.yaml`, `.yml` - YAML files

## Output Formats

### JSON Format (Default)
```json
{
  "timestamp": "2025-07-20T12:29:22.469",
  "summary": {
    "total_files": 14,
    "successful_files": 14,
    "error_files": 0,
    "average_text_length": 10758
  },
  "results": [
    {
      "success": true,
      "text_content": "This is the extracted text...",
      "text_length": 19310,
      "quality_score": 1.0,
      "file_path": "/app/scan_folder/README.md",
      "file_size": 20480
    }
  ]
}
```

### Text Format
```
Text Extraction Report - 2025-07-20 12:29:22
Total files: 14
Successful: 14
Failed: 0

✅ /app/scan_folder/README.md: 19310 chars
✅ /app/scan_folder/test_real_pipeline.txt: 258 chars
❌ /app/scan_folder/binary_file.bin: File not found
```

### Summary Format
```
============================================================
TEXT EXTRACTION SUMMARY
============================================================
Total files: 14
Successful extractions: 14
Failed extractions: 0
Average text length: 10758 characters
============================================================
```

## Architecture

### How It Works

1. **Script Execution**: `text_processor_dynamic.sh` creates a temporary Docker container
2. **Volume Mounting**: The target folder is mounted read-only into the container
3. **File Discovery**: `text_processor.py` scans the folder for supported file types
4. **Concurrent Processing**: Files are processed in parallel using asyncio
5. **Text Extraction**: Each file is read with appropriate encoding handling
6. **Report Generation**: Results are compiled into the requested output format
7. **Cleanup**: Container is automatically removed after completion

### Container Details

- **Image**: `mep-text-processor:latest`
- **Network**: `--network host` for local service access
- **Volumes**: Read-only mount of target folder
- **Environment**: `PROCESSING_PIPELINE_URL` for service communication
- **Lifetime**: Temporary container with auto-cleanup

## Performance Considerations

### Concurrency
- Default: 5 concurrent jobs
- Recommended: 10-20 for large folders
- Maximum: Limited by system resources

### Memory Usage
- Each file is loaded entirely into memory
- Large files (>100MB) may cause memory issues
- Consider file size when setting concurrency

### Processing Speed
- Text files: ~1-10ms per file
- Large files: ~100-1000ms per file
- Network files: Depends on network speed

## Error Handling

### File Access Errors
- Missing files are logged and skipped
- Permission errors are reported
- Network timeouts are handled gracefully

### Encoding Issues
- UTF-8 is tried first
- Falls back to latin-1, cp1252, iso-8859-1
- Binary files get placeholder text

### Container Errors
- Container failures are reported
- Temporary containers are cleaned up
- Exit codes indicate success/failure

## Integration with Processing Pipeline

The dynamic text processor can be integrated with the main processing pipeline:

```bash
# Extract text and send to processing pipeline
./core/text_processor_dynamic.sh /path/to/folder --pipeline-url http://localhost:8003
```

### Processing Pipeline Integration

1. **Text Extraction**: Dynamic processor extracts text from files
2. **Document Upload**: Files are uploaded to the core processor
3. **Pipeline Processing**: Processing pipeline handles text and embedding generation
4. **Status Tracking**: Job status is tracked through the pipeline

## Troubleshooting

### Common Issues

**Container fails to start**
```bash
# Check Docker is running
docker ps

# Check image exists
docker images | grep mep-text-processor
```

**Permission denied**
```bash
# Check folder permissions
ls -la /path/to/folder

# Run with sudo if needed
sudo ./core/text_processor_dynamic.sh /path/to/folder
```

**No files found**
```bash
# Check file extensions are supported
find /path/to/folder -type f | head -10

# Use --dry-run to see what would be processed
./core/text_processor_dynamic.sh /path/to/folder --dry-run
```

**Memory issues**
```bash
# Reduce concurrency
./core/text_processor_dynamic.sh /path/to/folder --concurrent 2

# Process smaller batches
./core/text_processor_dynamic.sh /path/to/folder --max-depth 0
```

### Debug Mode

Enable verbose logging:
```bash
# Set environment variable for debug logging
DEBUG=1 ./core/text_processor_dynamic.sh /path/to/folder
```

## Best Practices

### Performance
- Use appropriate concurrency for your system
- Process large folders in batches
- Monitor memory usage for large files

### Security
- Only mount folders you trust
- Use read-only mounts when possible
- Review extracted content before processing

### Reliability
- Use dry-run mode for testing
- Check file permissions before processing
- Monitor disk space for large extractions

## Comparison with Static Processing

| Feature | Dynamic Processing | Static Processing |
|---------|-------------------|-------------------|
| **Setup** | No configuration needed | Requires Docker Compose changes |
| **Flexibility** | Any folder, any time | Fixed folder locations |
| **Resource Usage** | Temporary containers | Permanent containers |
| **Maintenance** | Self-contained | Requires service management |
| **Performance** | On-demand | Always running |
| **Use Case** | Ad-hoc processing | Continuous monitoring |

## Future Enhancements

### Planned Features
- **PDF Support**: Extract text from PDF files
- **Image OCR**: Extract text from images using OCR
- **Compressed Files**: Handle zip, tar, gz archives
- **Database Integration**: Direct database text extraction
- **Cloud Storage**: Support for S3, GCS, Azure Blob

### Performance Improvements
- **Streaming Processing**: Handle very large files
- **Incremental Processing**: Only process changed files
- **Caching**: Cache extracted text for repeated access
- **Distributed Processing**: Multi-container processing

## Conclusion

The dynamic text processing system provides a flexible, powerful solution for extracting text from any folder on your system. It combines the convenience of dynamic container creation with robust text extraction capabilities, making it ideal for both ad-hoc processing and integration with larger document processing workflows. 