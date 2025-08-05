# Batch Folder Scanner

A command-line tool that scans folders and stores comprehensive file information in PostgreSQL database.

## Features

- **Recursive folder scanning** with configurable depth limits
- **Comprehensive file metadata** including size, type, permissions, timestamps
- **SHA256 checksums** for change detection
- **PostgreSQL storage** with optimized indexes
- **Session tracking** for monitoring scan progress
- **Change detection** - only updates files that have actually changed
- **Dry run mode** for testing without making changes

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

## Usage

### Basic Usage
```bash
python folder_scanner.py /path/to/folder
```

### Advanced Usage
```bash
# Scan with maximum depth of 3 levels
python folder_scanner.py /path/to/folder --max-depth 3

# Use custom session ID
python folder_scanner.py /path/to/folder --session-id my_scan_2024

# Dry run (no database changes)
python folder_scanner.py /path/to/folder --dry-run
```

### Docker-based Usage (Recommended)
```bash
# Build the Docker image first
./build_docker.sh

# Use the Docker scanner
./scan_folder.sh /path/to/folder
./scan_folder.sh /path/to/folder --max-depth 3 --dry-run
```

### Command Line Options

- `folder_path` (required): Path to the folder to scan
- `--max-depth`: Maximum directory depth to scan (default: unlimited)
- `--session-id`: Custom session ID (default: auto-generated timestamp)
- `--dry-run`: Show what would be done without making changes

## Examples

### Scan a documents folder
```bash
python folder_scanner.py /home/user/documents
```

### Scan with depth limit
```bash
python folder_scanner.py /home/user/projects --max-depth 2
```

### Test run without changes
```bash
python folder_scanner.py /home/user/documents --dry-run
```

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

## Logging

The script provides detailed logging:
- File processing progress
- Database operations
- Error conditions
- Session statistics
- Performance metrics

## Security Considerations

- **File permissions** are preserved and stored
- **Owner/group information** is captured
- **Checksums** provide integrity verification
- **Session isolation** prevents data corruption

## Integration with MEP AI NABOX

This batch scanner integrates with the MEP AI NABOX system:

- Uses the same PostgreSQL database
- Follows the same configuration patterns
- Compatible with existing monitoring tools
- Can be integrated into automated workflows

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

### Debug Mode

For detailed debugging, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG)
``` 