# Folder Scanner Utility

The Folder Scanner Utility is a powerful tool that can scan any folder and process all files and subfolders within it, using the same processing logic as the file watcher service.

## Features

- **Recursive Scanning**: Scan all subdirectories within a folder
- **Depth Control**: Limit the depth of recursive scanning
- **Concurrent Processing**: Process multiple files simultaneously
- **Dry Run Mode**: Preview what would be processed without actually processing
- **Comprehensive Reporting**: Generate detailed reports of processing results
- **Error Handling**: Robust error handling with detailed logging
- **File Validation**: Validates file types and sizes before processing

## Supported File Types

The scanner supports the same file types as the file watcher:

- **Documents**: PDF, DOCX, DOC, TXT, HTML, HTM
- **Images**: PNG, JPG, JPEG, GIF, BMP, TIFF
- **Spreadsheets**: CSV, XLSX, XLS

## Usage

### Using the Python Script Directly

```bash
# Basic usage - scan a folder recursively
python3 folder_scanner.py /path/to/folder

# Dry run - see what would be processed
python3 folder_scanner.py /path/to/folder --dry-run

# Limit recursive depth
python3 folder_scanner.py /path/to/folder --max-depth 3

# Non-recursive scan (only top-level files)
python3 folder_scanner.py /path/to/folder --no-recursive

# Control concurrency
python3 folder_scanner.py /path/to/folder --concurrent 10

# Save report to specific file
python3 folder_scanner.py /path/to/folder --save-report my_report.json
```

### Using the Shell Script Wrapper

```bash
# Basic usage
./scan_folder.sh /path/to/folder

# Dry run
./scan_folder.sh /path/to/folder --dry-run

# Limit depth
./scan_folder.sh /path/to/folder --max-depth 3

# Non-recursive
./scan_folder.sh /path/to/folder --no-recursive

# Control concurrency
./scan_folder.sh /path/to/folder --concurrent 10

# Save report
./scan_folder.sh /path/to/folder --save-report my_report.json
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Show what would be processed without actually processing | False |
| `--no-recursive` | Disable recursive scanning | False (recursive enabled) |
| `--max-depth <depth>` | Maximum depth for recursive scanning | No limit |
| `--concurrent <num>` | Number of concurrent processing tasks | 5 |
| `--save-report <file>` | Save processing report to specific file | Auto-generated filename |

## Environment Variables

The scanner uses the same environment variables as the file watcher:

- `CORE_PROCESSOR_URL`: URL of the core processor service (default: `http://core-processor:8001`)

**Note**: Files are processed in-place and are not moved to separate folders. The original folder structure and files remain unchanged.

## Output

### Console Output

The scanner provides real-time logging of:
- Files being scanned
- Files being processed
- Processing results
- Errors and warnings
- Final summary

### Processing Summary

After completion, a summary is displayed showing:
- Number of processed files
- Number of error files
- Number of skipped files
- Total files scanned

### JSON Report

A detailed JSON report is automatically generated containing:
- Scan timestamp
- List of processed files with metadata
- List of error files with error details
- List of skipped files with reasons
- Summary statistics

Example report structure:
```json
{
  "scan_timestamp": "2024-01-15T10:30:00.000Z",
  "processed_files": [
    {
      "file_path": "/path/to/file.pdf",
      "processed_at": "2024-01-15T10:30:05.000Z",
      "document_id": "doc_12345"
    }
  ],
  "error_files": [
    {
      "file_path": "/path/to/error.txt",
      "error_at": "2024-01-15T10:30:10.000Z",
      "error": "Processing failed"
    }
  ],
  "skipped_files": [
    {
      "file_path": "/path/to/unsupported.xyz",
      "reason": "Invalid file type or size",
      "skipped_at": "2024-01-15T10:30:15.000Z"
    }
  ],
  "summary": {
    "total_processed": 1,
    "total_errors": 1,
    "total_skipped": 1,
    "total_files": 3
  }
}
```

## Examples

### Example 1: Scan a Documents Folder

```bash
# Scan all documents in a folder
./scan_folder.sh /home/user/documents

# This will:
# - Recursively scan all subdirectories
# - Process all supported file types
# - Process files in-place (no movement)
# - Generate a detailed report
```

### Example 2: Preview Processing

```bash
# See what would be processed without actually doing it
./scan_folder.sh /home/user/documents --dry-run

# This will show:
# - Which files would be processed
# - Which files would be skipped
# - No files are actually moved or processed
```

### Example 3: Limited Depth Scan

```bash
# Only scan 2 levels deep
./scan_folder.sh /home/user/documents --max-depth 2

# This will:
# - Scan the main folder
# - Scan immediate subdirectories
# - Skip deeper subdirectories
```

### Example 4: High Concurrency Processing

```bash
# Process 20 files simultaneously
./scan_folder.sh /home/user/documents --concurrent 20

# Useful for:
# - Large folders with many files
# - Fast processing when system resources allow
```

## Integration with File Watcher

The folder scanner uses the same processing logic as the file watcher service, ensuring consistency in:

- File validation rules
- Document metadata creation
- Processing pipeline integration
- Error handling
- In-place processing (no file movement)

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the script has read access to the target folder
2. **Network Errors**: Check that the core processor service is running and accessible
3. **File Locks**: Some files may be locked by other processes

### Debug Mode

For detailed debugging, you can modify the logging level in the script:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Checking Service Status

Before running the scanner, ensure the core processor service is running:

```bash
curl http://core-processor:8001/health
```

## Performance Considerations

- **Concurrency**: Higher concurrency values can speed up processing but may overwhelm the system
- **File Size**: Large files (>100MB) are automatically skipped
- **Network**: Processing speed depends on network connectivity to the core processor
- **Disk I/O**: Since files are processed in-place, disk I/O is minimized

## Security Notes

- The scanner processes files in-place without moving them
- Ensure proper file permissions on target folders
- Consider using dry-run mode first for sensitive data
- The scanner does not modify file contents, only processes them 