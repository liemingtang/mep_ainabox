# Batch Processing System

## Overview

The batch processing system provides a Docker-based solution for processing files from the `file_processing_queue` table. It queries the database to get file information and dynamically mounts the necessary folders to process files within isolated Docker containers.

## Architecture

### Components

1. **`batch_process_file_queue.py`** - Main Python script that:
   - Queries the database for pending items
   - Groups items by folder for efficient mounting
   - Dynamically mounts folders to Docker containers
   - Manages the processing workflow

2. **`batch_process_file_queue.sh`** - Shell script wrapper that:
   - Builds and runs the Docker container
   - Mounts the Docker socket for Docker-in-Docker capability
   - Passes configuration and arguments

3. **`process_file_processing_queue.py`** - Worker script that:
   - Processes items from JSON file (when running in container)
   - Finds files in mounted folders
   - Runs text processing on files
   - Updates queue status

4. **`text_processor.py`** - Simple text processor that:
   - Analyzes text files
   - Extracts basic statistics
   - Saves results to output directory

## Database Schema

The system uses the existing `file_processing_queue` table with the following key fields:

- `id` - Unique identifier
- `file_info_id` - Foreign key to `file_info` table
- `file_path` - Full path to the file
- `filename` - Name of the file
- `priority` - Processing priority (higher = more important)
- `processor_type` - Type of processor to use
- `status` - Current status (pending, processing, completed, failed)
- `error_message` - Error details if processing failed
- `retry_count` - Number of retry attempts
- `max_retries` - Maximum retry attempts allowed

## Usage

### Basic Usage

```bash
# Process a batch of items
./batch_process_file_queue.sh --limit 10

# Process items with specific processor type
./batch_process_file_queue.sh --processor-type text_processor

# Dry run to see what would be processed
./batch_process_file_queue.sh --dry-run --limit 5
```

### Advanced Usage

```bash
# Process with additional worker arguments
./batch_process_file_queue.sh --limit 5 --script-args --continuous

# Process specific processor type with custom arguments
./batch_process_file_queue.sh --processor-type default --script-args --interval 60
```

## How It Works

### 1. Database Query
The batch processor queries the database to get pending items:

```sql
SELECT q.id, q.file_info_id, q.file_path, q.filename, q.priority, 
       q.processor_type, q.metadata, q.retry_count, q.max_retries,
       f.parent_directory
FROM file_processing_queue q
JOIN file_info f ON q.file_info_id = f.id
WHERE q.status = 'pending'
ORDER BY q.priority DESC, q.created_at ASC
LIMIT ?
```

### 2. Folder Grouping
Items are grouped by their parent directory to minimize the number of folder mounts:

```python
folder_groups = {
    '/media/lie/DATA2/ai_scan_folder/': [item1, item2],
    '/home/lie/repo_mep/mep_ainabox/watch_folder/': [item3]
}
```

### 3. Dynamic Mounting
Each folder group is mounted to the Docker container:

```bash
docker run --rm --network host \
  -v /media/lie/DATA2/ai_scan_folder/:/mnt/ai_scan_folder:ro \
  -v /home/lie/repo_mep/mep_ainabox/watch_folder/:/mnt/watch_folder:ro \
  -v /tmp/items.json:/app/items.json:ro \
  -e ITEMS_FILE=/app/items.json \
  -e MOUNT_POINTS=/mnt/ai_scan_folder,/mnt/watch_folder \
  mep-folder-scanner:latest \
  --entrypoint python3 /app/process_file_processing_queue.py
```

### 4. File Processing
The worker script:
- Loads items from the JSON file
- Finds files in the mounted folders
- Runs the appropriate processor (e.g., text_processor.py)
- Updates the queue status

## Docker Configuration

### Docker Image
The system uses the `mep-folder-scanner:latest` image which includes:
- Python 3.11 with required dependencies
- Docker CLI for Docker-in-Docker capability
- All processing scripts

### Docker Socket Mounting
The shell script mounts the Docker socket to enable Docker-in-Docker:

```bash
-v /var/run/docker.sock:/var/run/docker.sock
```

This allows the container to run Docker commands to spawn worker containers.

## Error Handling

### File Not Found
If a file cannot be found in any mounted folder, the item is marked as failed with an error message.

### Processing Failures
If the text processor fails, the item is marked as failed and the error is recorded.

### Retry Logic
Items can be retried up to `max_retries` times before being permanently marked as failed.

## Status Values

- **pending** - Item is waiting to be processed
- **processing** - Item is currently being processed
- **completed** - Item was successfully processed
- **failed** - Item failed to process (with error message)
- **cancelled** - Item was cancelled

## Priority System

Items are processed in order of:
1. Priority (higher numbers first)
2. Creation time (older items first)

## Examples

### Process All Pending Items
```bash
./batch_process_file_queue.sh --limit 100
```

### Process Only Text Files
```bash
# First, queue text files
./queue_file_processing.sh --file-type .txt --processor-type text_processor

# Then process them
./batch_process_file_queue.sh --processor-type text_processor
```

### Monitor Processing
```bash
# Check queue status
docker exec -it mep-postgres psql -U mep_user -d mep_ainabox -c "
SELECT filename, status, created_at, completed_at 
FROM file_processing_queue 
ORDER BY created_at DESC LIMIT 10;
"
```

## Integration Points

### With Folder Scanner
The batch processor works with the folder scanner system:
1. `scan_folder.sh` scans folders and populates `file_info`
2. `queue_file_processing.sh` adds files to `file_processing_queue`
3. `batch_process_file_queue.sh` processes the queued files

### With Text Processor
The system can be extended with different processors:
- `text_processor.py` - Basic text analysis
- Custom processors can be added for different file types
- Processors are called via Docker with mounted folders

## Security Considerations

- Folders are mounted as read-only (`:ro`)
- Docker socket mounting requires appropriate permissions
- Containers run with limited user privileges
- Temporary files are cleaned up after processing

## Performance

- Items are processed in batches to optimize resource usage
- Folder grouping minimizes the number of Docker mounts
- Database connections are pooled for efficiency
- Processing timeouts prevent hanging containers

## Troubleshooting

### Common Issues

1. **Docker not found**: Ensure Docker CLI is installed in the container
2. **Permission denied**: Check Docker socket permissions
3. **File not found**: Verify file paths in the database
4. **Database connection failed**: Check PostgreSQL configuration

### Debug Mode
Use dry-run mode to see what would be processed:
```bash
./batch_process_file_queue.sh --dry-run --limit 5
```

### Logs
Check container logs for detailed error information:
```bash
docker logs <container_name>
``` 