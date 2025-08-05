# Queue File Processing

This module provides functionality to queue files from the `file_info` table for processing in the `file_processing_queue` table. The system runs in a Docker container for consistency and isolation.

## Overview

The queue processing system allows you to:
- Select files from the database based on various filters
- Add them to a processing queue with priorities
- Track processing status and statistics
- Support different processor types for different workflows

## Database Schema

### file_processing_queue Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| file_info_id | INTEGER | Reference to file_info table |
| file_path | TEXT | Full path to the file |
| filename | TEXT | Name of the file |
| priority | INTEGER | Processing priority (1-10, default: 5) |
| status | TEXT | Current status (pending, processing, completed, failed, cancelled) |
| created_at | TIMESTAMP | When the item was added to queue |
| scheduled_at | TIMESTAMP | When processing should start |
| started_at | TIMESTAMP | When processing actually started |
| completed_at | TIMESTAMP | When processing completed |
| error_message | TEXT | Error message if processing failed |
| retry_count | INTEGER | Number of retry attempts |
| max_retries | INTEGER | Maximum retry attempts (default: 3) |
| processor_type | TEXT | Type of processor to use |
| metadata | JSONB | Additional metadata about the file |

## Usage

### Basic Commands

```bash
# Show queue statistics
./queue_file_processing.sh --stats

# Add all files to queue
./queue_file_processing.sh

# Add only PDF files with high priority
./queue_file_processing.sh --file-type .pdf --priority 8

# Add text files with low priority
./queue_file_processing.sh --file-type .txt --priority 3

# Add files by MIME type
./queue_file_processing.sh --mime-type application/pdf

# Dry run to see what would be queued
./queue_file_processing.sh --dry-run --limit 10
```

### Filtering Options

- `--file-type <type>`: Filter by file extension (e.g., '.pdf', '.txt')
- `--mime-type <type>`: Filter by MIME type (e.g., 'application/pdf')
- `--min-size <bytes>`: Minimum file size in bytes
- `--max-size <bytes>`: Maximum file size in bytes
- `--files-only`: Only process files (exclude directories)
- `--directories-only`: Only process directories
- `--limit <number>`: Maximum number of files to queue

### Queue Options

- `--priority <1-10>`: Processing priority (default: 5)
- `--processor-type <type>`: Processor type (default: 'default')
- `--dry-run`: Show what would be done without making changes
- `--stats`: Show queue statistics

## Queue Status Values

- **pending**: Item is waiting to be processed
- **processing**: Item is currently being processed
- **completed**: Item has been successfully processed
- **failed**: Item failed to process (may be retried)
- **cancelled**: Item was cancelled and won't be retried

## Priority System

- **1-3**: Low priority (processed last)
- **4-6**: Normal priority (default)
- **7-9**: High priority (processed first)
- **10**: Critical priority (processed immediately)

## Examples

### Queue all PDF files with high priority
```bash
./queue_file_processing.sh --file-type .pdf --priority 8
```

### Queue large files only
```bash
./queue_file_processing.sh --min-size 1000000 --files-only
```

### Queue text files for text processing
```bash
./queue_file_processing.sh --file-type .txt --processor-type text_processor
```

### Check queue status
```bash
./queue_file_processing.sh --stats
```

## Docker Integration

The queue processing script runs in a Docker container using the same image as the folder scanner (`mep-folder-scanner:latest`). This provides:

- **Consistency**: Same environment for all batch operations
- **Isolation**: No conflicts with host system dependencies
- **Portability**: Works across different systems
- **Security**: Runs in a contained environment

### Docker Features

- **Network**: Uses host network for database connectivity
- **Volumes**: Mounts config directory for database configuration
- **Entrypoint**: Overrides default entrypoint to run queue processing script
- **Cleanup**: Automatically removes containers after execution

## Integration

This queue system can be integrated with:
- File processing workers
- Background job systems
- Workflow engines
- Monitoring systems

The queue entries can be processed by workers that:
1. Pick up pending items
2. Update status to 'processing'
3. Process the file
4. Update status to 'completed' or 'failed'
5. Handle retries for failed items 