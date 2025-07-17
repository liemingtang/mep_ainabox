# Folder Scanner - Quick Reference

## Command Line Usage

### Basic Commands
```bash
# Scan folder recursively
./scan_folder.sh /path/to/folder

# Dry run (preview only)
./scan_folder.sh /path/to/folder --dry-run

# Non-recursive scan
./scan_folder.sh /path/to/folder --no-recursive

# Limit depth
./scan_folder.sh /path/to/folder --max-depth 3

# High concurrency
./scan_folder.sh /path/to/folder --concurrent 20
```

### Python Script Directly
```bash
# Basic usage
python3 folder_scanner.py /path/to/folder

# With options
python3 folder_scanner.py /path/to/folder --dry-run --max-depth 2 --concurrent 10
```

## API Usage

### HTTP Endpoint
```bash
# Scan folder via API
curl -X POST "http://file-watcher:8009/api/v1/watch/scan-folder" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/folder",
    "recursive": true,
    "max_depth": 3,
    "concurrent_limit": 5,
    "dry_run": false
  }'
```

### Python Integration
```python
from folder_scanner import FolderScanner

# Create scanner
scanner = FolderScanner(dry_run=False)

# Process folder
await scanner.process_folder(
    folder_path="/path/to/folder",
    recursive=True,
    max_depth=3,
    concurrent_limit=5
)

# Access results
print(f"Processed: {len(scanner.processed_files)}")
print(f"Errors: {len(scanner.error_files)}")
print(f"Skipped: {len(scanner.skipped_files)}")
```

## Supported File Types

| Type | Extensions |
|------|------------|
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.html`, `.htm` |
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff` |
| Spreadsheets | `.csv`, `.xlsx`, `.xls` |

## Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | false | Preview without processing |
| `--no-recursive` | flag | false | Disable subdirectory scanning |
| `--max-depth` | int | none | Maximum scan depth |
| `--concurrent` | int | 5 | Concurrent processing limit |
| `--save-report` | string | auto | Custom report filename |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CORE_PROCESSOR_URL` | `http://core-processor:8001` | Core processor service URL |

**Note**: Files are processed in-place and are not moved to separate folders.

## Output Files

### Console Output
- Real-time processing status
- File validation results
- Error messages
- Final summary

### JSON Report
- Scan timestamp
- Processed files list
- Error files with details
- Skipped files with reasons
- Summary statistics

## Common Use Cases

### 1. Initial Data Import
```bash
# Scan entire document repository
./scan_folder.sh /home/user/documents --concurrent 10
```

### 2. Preview Processing
```bash
# See what would be processed
./scan_folder.sh /home/user/documents --dry-run
```

### 3. Limited Scope
```bash
# Only scan 2 levels deep
./scan_folder.sh /home/user/documents --max-depth 2
```

### 4. Top-Level Only
```bash
# Skip subdirectories
./scan_folder.sh /home/user/documents --no-recursive
```

### 5. High Performance
```bash
# Process many files quickly
./scan_folder.sh /home/user/documents --concurrent 20
```

## Error Handling

### Common Issues
- **Permission denied**: Check file/folder permissions
- **Service unavailable**: Ensure core processor is running
- **Disk space**: Check available space in processed/error folders
- **File locks**: Some files may be in use by other processes

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tips

- Use `--concurrent` to match your system's capabilities
- Use `--max-depth` to limit scanning scope
- Use `--dry-run` first to estimate processing time
- Monitor disk I/O and network connectivity

## Integration Notes

- Uses same processing logic as file watcher
- Compatible with existing core processor
- Maintains file integrity (processes in-place, doesn't modify)
- Generates detailed audit trails 