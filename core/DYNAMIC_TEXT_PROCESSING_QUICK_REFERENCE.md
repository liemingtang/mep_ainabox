# Dynamic Text Processing - Quick Reference

## Quick Commands

### Basic Usage
```bash
# Extract text from any folder
./core/text_processor_dynamic.sh /path/to/folder

# Preview what would be processed
./core/text_processor_dynamic.sh /path/to/folder --dry-run

# Get summary output
./core/text_processor_dynamic.sh /path/to/folder --output summary
```

### Common Examples
```bash
# Process external drive
./core/text_processor_dynamic.sh /media/user/USB_DRIVE/documents

# Process current directory (top level only)
./core/text_processor_dynamic.sh . --max-depth 0

# High-performance processing
./core/text_processor_dynamic.sh /large/folder --concurrent 20

# Process specific depth
./core/text_processor_dynamic.sh /path/to/folder --max-depth 2

# Non-recursive processing
./core/text_processor_dynamic.sh /path/to/folder --no-recursive
```

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Preview without processing | `--dry-run` |
| `--max-depth N` | Maximum directory depth | `--max-depth 2` |
| `--concurrent N` | Concurrent jobs | `--concurrent 10` |
| `--output FORMAT` | Output format | `--output summary` |
| `--no-recursive` | Don't scan subdirectories | `--no-recursive` |

## Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `json` | Detailed JSON report | Integration, analysis |
| `text` | Human-readable text | Quick review |
| `summary` | Brief statistics | Overview |

## Supported File Types

### Text Files
- `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`

### Source Code
- `.py`, `.js`, `.java`, `.cpp`, `.c`, `.h`, `.php`, `.rb`, `.go`, `.rs`, `.swift`, `.kt`

### Configuration & Logs
- `.log`, `.out`, `.err`, `.conf`, `.cfg`, `.ini`, `.yaml`, `.yml`

## Performance Tips

### For Large Folders
```bash
# Use high concurrency
./core/text_processor_dynamic.sh /large/folder --concurrent 20

# Process in batches by depth
./core/text_processor_dynamic.sh /large/folder --max-depth 1
./core/text_processor_dynamic.sh /large/folder --max-depth 2
```

### For Network Drives
```bash
# Use lower concurrency for network stability
./core/text_processor_dynamic.sh /mnt/network/folder --concurrent 5
```

### For Testing
```bash
# Always test with dry-run first
./core/text_processor_dynamic.sh /path/to/folder --dry-run

# Test with small subset
./core/text_processor_dynamic.sh /path/to/folder --max-depth 0
```

## Troubleshooting

### Common Issues

**Permission Denied**
```bash
# Check permissions
ls -la /path/to/folder

# Run with sudo if needed
sudo ./core/text_processor_dynamic.sh /path/to/folder
```

**No Files Found**
```bash
# Check what files exist
find /path/to/folder -type f | head -10

# Use dry-run to see what would be processed
./core/text_processor_dynamic.sh /path/to/folder --dry-run
```

**Container Fails**
```bash
# Check Docker is running
docker ps

# Check image exists
docker images | grep mep-text-processor

# Rebuild image if needed
docker build -t mep-text-processor:latest core/processors/text_processor/
```

## Integration Examples

### With Processing Pipeline
```bash
# Extract text and process through pipeline
./core/text_processor_dynamic.sh /path/to/folder --pipeline-url http://localhost:8003
```

### Batch Processing
```bash
# Process multiple folders
for folder in /path/to/folder1 /path/to/folder2 /path/to/folder3; do
    ./core/text_processor_dynamic.sh "$folder" --output summary
done
```

### Scheduled Processing
```bash
# Add to crontab for regular processing
0 2 * * * /path/to/mep_ainabox/core/text_processor_dynamic.sh /path/to/documents --output json
```

## Output Examples

### Summary Output
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

### Text Output
```
Text Extraction Report - 2025-07-20 12:29:22
Total files: 14
Successful: 14
Failed: 0

✅ /app/scan_folder/README.md: 19310 chars
✅ /app/scan_folder/test.txt: 258 chars
```

### JSON Output
```json
{
  "timestamp": "2025-07-20T12:29:22.469",
  "summary": {
    "total_files": 14,
    "successful_files": 14,
    "error_files": 0,
    "average_text_length": 10758
  },
  "results": [...]
}
```

## Best Practices

1. **Always test first**: Use `--dry-run` before processing large folders
2. **Monitor resources**: Use appropriate concurrency for your system
3. **Check permissions**: Ensure read access to target folders
4. **Use appropriate output**: JSON for integration, summary for quick review
5. **Process in batches**: Use `--max-depth` for large folder structures 