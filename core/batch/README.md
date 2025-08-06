# Batch Processing System

A comprehensive batch processing system that scans folders, queues files for processing, and processes them using Docker containers. The system consists of three main execution steps that work together to provide a complete file processing pipeline.

## Execution Steps

The batch processing system follows a three-step workflow:

### 1. Scan Folder (`scan_folder.sh`)
Scans directories recursively and stores comprehensive file information in the PostgreSQL database.

### 2. Queue File Processing (`queue_file_processing.sh`)
Adds files from the `file_info` table to the `file_processing_queue` table for processing.

### 3. Process Queue Worker (`process_queue_worker.sh`)
Processes files from the queue using the specified processor types.

## Quick Start

### Step 1: Scan a folder
```bash
# Scan a documents folder
./scan_folder.sh /path/to/documents

# Scan with depth limit
./scan_folder.sh /path/to/documents --max-depth 3

# Dry run to see what would be scanned
./scan_folder.sh /path/to/documents --dry-run
```

### Step 2: Queue files for processing
```bash
# Queue all files
./queue_file_processing.sh

# Queue only PDF files with high priority
./queue_file_processing.sh --file-type .pdf --priority 8

# Queue text files with custom processor
./queue_file_processing.sh --file-type .txt --processor-type text_processor

# Show queue statistics
./queue_file_processing.sh --stats
```

### Step 3: Process the queue
```bash
# Process a batch of items
./process_queue_worker.sh --limit 10

# Process continuously
./process_queue_worker.sh --continuous --interval 30

# Process specific processor type
./process_queue_worker.sh --processor-type text_processor

# Dry run to see what would be processed
./process_queue_worker.sh --dry-run --limit 5
```

## Complete Workflow Examples

### Example 1: Process PDF Documents
```bash
# 1. Scan the documents folder
./scan_folder.sh /home/user/documents

# 2. Queue PDF files for processing
./queue_file_processing.sh --file-type .pdf --priority 8

# 3. Process the queue
./process_queue_worker.sh --limit 20
```

### Example 2: Process Text Files Continuously
```bash
# 1. Scan a project folder
./scan_folder.sh /home/user/projects --max-depth 2

# 2. Queue text files
./queue_file_processing.sh --file-type .txt --processor-type text_processor

# 3. Process continuously
./process_queue_worker.sh --processor-type text_processor --continuous --interval 60
```

### Example 3: Process Large Files Only
```bash
# 1. Scan a data folder
./scan_folder.sh /home/user/data

# 2. Queue large files (>1MB)
./queue_file_processing.sh --min-size 1000000 --files-only --priority 7

# 3. Process in batches
./process_queue_worker.sh --limit 5
```

## Features

- **Recursive folder scanning** with configurable depth limits
- **Comprehensive file metadata** including size, type, permissions, timestamps
- **SHA256 checksums** for change detection
- **PostgreSQL storage** with optimized indexes
- **Session tracking** for monitoring scan progress
- **Change detection** - only updates files that have actually changed
- **Dry run mode** for testing without making changes
- **Priority-based queue processing**
- **Multiple processor types** support
- **Continuous processing** mode
- **Docker-based isolation** for consistent processing

## Database Schema

### `file_info` Table
Stores detailed information about each file/directory:

- `id` - Primary key
- `file_path` - Full absolute path (unique)
- `filename` - Just the filename
- `file_size` - Size in bytes
- `file_type` - File extension
- `mime_type` - MIME type detection
- `checksum` - SHA256 hash for change detection
- `created_time` - File creation timestamp
- `modified_time` - Last modification timestamp
- `accessed_time` - Last access timestamp
- `is_directory` - Boolean flag
- `parent_directory` - Parent directory path
- `depth` - Directory depth from root
- `permissions` - File permissions (octal)
- `owner` - File owner
- `group_name` - File group
- `scan_timestamp` - When this record was created
- `last_checked` - When this file was last scanned
- `status` - File status (active, deleted, etc.)
- `metadata` - JSONB field for additional metadata

### `file_processing_queue` Table
Stores files queued for processing:

- `id` - Primary key
- `file_info_id` - Reference to file_info table
- `file_path` - Full path to the file
- `filename` - Name of the file
- `priority` - Processing priority (1-10, default: 5)
- `status` - Current status (pending, processing, completed, failed, cancelled)
- `created_at` - When the item was added to queue
- `scheduled_at` - When processing should start
- `started_at` - When processing actually started
- `completed_at` - When processing completed
- `error_message` - Error message if processing failed
- `retry_count` - Number of retry attempts
- `max_retries` - Maximum retry attempts (default: 3)
- `processor_type` - Type of processor to use
- `metadata` - JSONB field for additional metadata

### `scan_sessions` Table
Tracks scanning sessions:

- `id` - Primary key
- `session_id` - Unique session identifier
- `folder_path` - Path being scanned
- `started_at` - Session start time
- `completed_at` - Session completion time
- `total_files` - Total files found
- `processed_files` - Successfully processed files
- `failed_files` - Failed files
- `status` - Session status (running, completed, failed)
- `metadata` - JSONB field for session metadata

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL is running and accessible

3. Make sure the configuration file exists at `../config/main.yaml`

4. Build the Docker image:
```bash
./build_docker.sh
```

## Usage

### Step 1: Scan Folder

#### Basic Usage
```bash
python folder_scanner.py /path/to/folder
```

#### Advanced Usage
```bash
# Scan with maximum depth of 3 levels
python folder_scanner.py /path/to/folder --max-depth 3

# Use custom session ID
python folder_scanner.py /path/to/folder --session-id my_scan_2024

# Dry run (no database changes)
python folder_scanner.py /path/to/folder --dry-run
```

#### Docker-based Usage (Recommended)
```bash
# Use the Docker scanner
./scan_folder.sh /path/to/folder
./scan_folder.sh /path/to/folder --max-depth 3 --dry-run
```

#### Command Line Options

- `folder_path` (required): Path to the folder to scan
- `--max-depth`: Maximum directory depth to scan (default: unlimited)
- `--session-id`: Custom session ID (default: auto-generated timestamp)
- `--dry-run`: Show what would be done without making changes
- `--force`: Force scan all files regardless of changes

### Step 2: Queue File Processing

#### Basic Commands
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

#### Filtering Options

- `--file-type <type>`: Filter by file extension (e.g., '.pdf', '.txt')
- `--mime-type <type>`: Filter by MIME type (e.g., 'application/pdf')
- `--min-size <bytes>`: Minimum file size in bytes
- `--max-size <bytes>`: Maximum file size in bytes
- `--files-only`: Only process files (exclude directories)
- `--directories-only`: Only process directories
- `--limit <number>`: Maximum number of files to queue

#### Queue Options

- `--priority <1-10>`: Processing priority (default: 5)
- `--processor-type <type>`: Processor type (default: 'default')
- `--dry-run`: Show what would be done without making changes
- `--stats`: Show queue statistics

### Step 3: Process Queue Worker

#### Basic Commands
```bash
# Process a batch of items
./process_queue_worker.sh --limit 10

# Process items with specific processor type
./process_queue_worker.sh --processor-type text_processor

# Process continuously
./process_queue_worker.sh --continuous --interval 30

# Dry run to see what would be processed
./process_queue_worker.sh --dry-run --limit 5
```

#### Worker Options

- `--processor-type <type>`: Only process items with this processor type
- `--limit <number>`: Maximum items to process per batch (default: 10)
- `--continuous`: Run continuously
- `--interval <seconds>`: Interval between batches in seconds (default: 30)
- `--dry-run`: Show what would be processed without making changes

## Priority System

- **1-3**: Low priority (processed last)
- **4-6**: Normal priority (default)
- **7-9**: High priority (processed first)
- **10**: Critical priority (processed immediately)

## Queue Status Values

- **pending**: Item is waiting to be processed
- **processing**: Item is currently being processed
- **completed**: Item has been successfully processed
- **failed**: Item failed to process (may be retried)
- **cancelled**: Item was cancelled and won't be retried

## Configuration

The script uses the PostgreSQL configuration from `../config/main.yaml`:

```yaml
core:
  storage:
    postgresql:
      host: "localhost"
      port: 5432
      database: "mep_ainabox"
      user: "mep_user"
      password: "mep_password"
      pool_size: 10
```

## Performance Features

- **Connection pooling** for efficient database connections
- **Batch processing** with progress updates every 100 files
- **Optimized indexes** on frequently queried columns
- **Change detection** to avoid unnecessary updates
- **Asynchronous processing** for better performance
- **Docker-based isolation** for consistent processing environments

## Monitoring

### Check scan sessions
```sql
SELECT * FROM scan_sessions ORDER BY started_at DESC LIMIT 10;
```

### Check file statistics
```sql
SELECT 
    COUNT(*) as total_files,
    SUM(CASE WHEN is_directory THEN 1 ELSE 0 END) as directories,
    SUM(CASE WHEN NOT is_directory THEN 1 ELSE 0 END) as files,
    SUM(file_size) as total_size
FROM file_info 
WHERE status = 'active';
```

### Check queue status
```sql
SELECT 
    status,
    COUNT(*) as count,
    AVG(priority) as avg_priority
FROM file_processing_queue 
GROUP BY status;
```

### Find changed files
```sql
SELECT filename, file_path, modified_time, last_checked
FROM file_info 
WHERE modified_time > last_checked
ORDER BY modified_time DESC;
```

## Error Handling

- **File access errors** are logged but don't stop the scan
- **Database connection errors** cause the scan to fail gracefully
- **Permission errors** are logged with file path
- **Checksum calculation errors** are logged but file is still processed
- **Queue processing errors** are logged and items can be retried
- **Docker container errors** are handled with proper cleanup

## Logging

The scripts provide detailed logging:
- File processing progress
- Database operations
- Error conditions
- Session statistics
- Performance metrics
- Queue processing status

## Security Considerations

- **File permissions** are preserved and stored
- **Owner/group information** is captured
- **Checksums** provide integrity verification
- **Session isolation** prevents data corruption
- **Docker isolation** provides process isolation
- **Database transactions** ensure data consistency

## Integration with MEP AI NABOX

This batch processing system integrates with the MEP AI NABOX system:

- Uses the same PostgreSQL database
- Follows the same configuration patterns
- Compatible with existing monitoring tools
- Can be integrated into automated workflows
- Supports the same processor types as the main system

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running
   - Verify connection details in config
   - Check firewall settings

2. **Permission denied errors**
   - Ensure script has read access to target folder
   - Check file permissions

3. **Memory issues with large folders**
   - Use `--max-depth` to limit recursion
   - Process folders in smaller batches

4. **Slow performance**
   - Check database indexes are created
   - Monitor disk I/O
   - Consider running during off-peak hours

5. **Docker image not found**
   - Run `./build_docker.sh` to build the image
   - Check Docker is running

6. **Queue processing stuck**
   - Check for failed items in the queue
   - Verify processor types are available
   - Check database connections

### Debug Mode

For detailed debugging, modify the logging level in the scripts:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Docker Debugging

```bash
# Check Docker container logs
docker logs <container_name>

# Run container interactively
docker run -it --rm mep-folder-scanner:latest /bin/bash

# Check container status
docker ps -a
``` 