# Dynamic Folder Scanning - Quick Reference

## Quick Commands

### One-Time Scan
```bash
# Scan any folder
./core/scan_folder_dynamic.sh /path/to/folder

# Preview scan (dry run)
./core/scan_folder_dynamic.sh /path/to/folder --dry-run

# High concurrency
./core/scan_folder_dynamic.sh /path/to/folder --concurrent 10

# Limited depth
./core/scan_folder_dynamic.sh /path/to/folder --max-depth 3
```

### Continuous Watching
```bash
# Watch folder for new files
./core/watch_folder_dynamic.sh /path/to/folder

# Scan once and exit
./core/watch_folder_dynamic.sh /path/to/folder --scan-once
```

## Common Use Cases

### External Drives
```bash
./core/scan_folder_dynamic.sh /media/user/USB_DRIVE/documents
./core/watch_folder_dynamic.sh /media/user/USB_DRIVE/documents
```

### Network Shares
```bash
./core/scan_folder_dynamic.sh /mnt/network_share/documents
./core/watch_folder_dynamic.sh /mnt/network_share/documents
```

### Cloud Storage
```bash
./core/scan_folder_dynamic.sh /home/user/Dropbox/documents
./core/watch_folder_dynamic.sh /home/user/Google\ Drive/documents
```

## Prerequisites

1. **Build Docker Image**:
   ```bash
   docker build -t mep-file-watcher:latest core/file_watcher/
   ```

2. **Check Services**:
   ```bash
   curl http://localhost:8001/health
   ```

## Troubleshooting

- **Permission denied**: Check folder permissions
- **Image not found**: Build the Docker image
- **Connection refused**: Check if core processor is running
- **Folder not found**: Verify path exists

## Options Summary

| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Preview without processing | `--dry-run` |
| `--no-recursive` | Skip subdirectories | `--no-recursive` |
| `--max-depth N` | Limit scan depth | `--max-depth 3` |
| `--concurrent N` | Concurrent tasks | `--concurrent 10` |
| `--save-report` | Save report file | `--save-report report.json` |
| `--scan-once` | Scan once and exit | `--scan-once` |

## Security Features

- ✅ Read-only folder mounts
- ✅ Temporary containers (auto-cleanup)
- ✅ Unique container names
- ✅ Network isolation 