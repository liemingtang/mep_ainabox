# Dynamic Folder Scanning

This document describes the dynamic folder scanning system that allows you to scan any folder on your system without modifying Docker Compose configurations.

## Overview

The dynamic folder scanning system consists of two main scripts:

1. **`scan_folder_dynamic.sh`** - One-time folder scanning
2. **`watch_folder_dynamic.sh`** - Continuous folder monitoring

Both scripts create temporary Docker containers that mount any folder on-the-fly and process files using the MEP AI NABOX processing pipeline.

## Features

- ✅ **Dynamic Mounting**: Mount any folder without Docker Compose changes
- ✅ **Read-Only Access**: Folders are mounted read-only for security
- ✅ **Network Flexibility**: Automatically detects localhost vs remote services
- ✅ **Temporary Containers**: Containers are automatically cleaned up
- ✅ **Comprehensive Options**: Support for all folder scanner options
- ✅ **Cross-Platform**: Works with any folder path accessible to Docker

## Scripts

### 1. Dynamic Folder Scanner (`scan_folder_dynamic.sh`)

**Purpose**: Scan any folder once and process all files found.

**Usage**:
```bash
./core/scan_folder_dynamic.sh <folder_path> [options]
```

**Options**:
- `--dry-run, -d` - Preview without processing
- `--no-recursive` - Disable subdirectory scanning
- `--max-depth <depth>` - Limit scan depth
- `--concurrent <num>` - Number of concurrent tasks (default: 5)
- `--save-report <file>` - Save processing report
- `--processor-url <url>` - Core processor URL (default: localhost:8001)
- `--help, -h` - Show help

**Examples**:
```bash
# Scan external drive
./core/scan_folder_dynamic.sh /media/user/external_drive/documents

# Preview scan
./core/scan_folder_dynamic.sh /home/user/documents --dry-run

# Limited depth scan
./core/scan_folder_dynamic.sh /path/to/folder --max-depth 3

# High concurrency
./core/scan_folder_dynamic.sh /path/to/folder --concurrent 10

# Save report
./core/scan_folder_dynamic.sh /path/to/folder --save-report my_report.json
```

### 2. Dynamic File Watcher (`watch_folder_dynamic.sh`)

**Purpose**: Continuously monitor any folder for new files.

**Usage**:
```bash
./core/watch_folder_dynamic.sh <folder_path> [options]
```

**Options**:
- `--scan-once` - Scan once and exit (default: continuous watching)
- `--processor-url <url>` - Core processor URL
- `--container-name <name>` - Custom container name
- `--help, -h` - Show help

**Examples**:
```bash
# Watch folder continuously
./core/watch_folder_dynamic.sh /path/to/folder

# Scan once and exit
./core/watch_folder_dynamic.sh /media/user/external_drive/documents --scan-once

# Custom processor URL
./core/watch_folder_dynamic.sh /path/to/folder --processor-url http://192.168.1.100:8001
```

## Use Cases

### 1. External Drives
```bash
# Scan external USB drive
./core/scan_folder_dynamic.sh /media/user/USB_DRIVE/documents

# Watch external drive for new files
./core/watch_folder_dynamic.sh /media/user/USB_DRIVE/documents
```

### 2. Network Shares
```bash
# Scan network share
./core/scan_folder_dynamic.sh /mnt/network_share/documents

# Watch network share
./core/watch_folder_dynamic.sh /mnt/network_share/documents
```

### 3. Cloud Storage Sync Folders
```bash
# Scan Dropbox/Google Drive sync folder
./core/scan_folder_dynamic.sh /home/user/Dropbox/documents

# Watch sync folder
./core/watch_folder_dynamic.sh /home/user/Google\ Drive/documents
```

### 4. Temporary Folders
```bash
# Scan temporary download folder
./core/scan_folder_dynamic.sh /tmp/downloads

# Watch downloads folder
./core/watch_folder_dynamic.sh /home/user/Downloads
```

## Technical Details

### How It Works

1. **Path Resolution**: Script resolves absolute path of target folder
2. **Docker Command Building**: Constructs Docker run command with appropriate mounts
3. **Network Detection**: Automatically detects localhost vs remote services
4. **Container Creation**: Creates temporary container with unique name
5. **Volume Mounting**: Mounts target folder read-only in container
6. **Processing**: Runs folder scanner or file watcher in container
7. **Cleanup**: Container is automatically removed when done

### Security Features

- **Read-Only Mounts**: All folders are mounted read-only (`:ro`)
- **Temporary Containers**: Containers are removed after use (`--rm`)
- **Unique Names**: Container names include timestamps to avoid conflicts
- **Network Isolation**: Uses appropriate network mode for security

### Network Modes

- **Host Network**: Used when processor URL contains `localhost`
- **Bridge Network**: Used for remote services (requires `mep-ainabox_default` network)

## Prerequisites

### 1. Docker Image
The scripts require the `mep-file-watcher:latest` Docker image. Build it with:
```bash
docker build -t mep-file-watcher:latest core/file_watcher/
```

### 2. Docker Permissions
Ensure your user can run Docker commands:
```bash
# Add user to docker group (if not already done)
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### 3. Service Availability
Ensure the core processor service is running:
```bash
# Check if service is available
curl http://localhost:8001/health
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Error: Permission denied when accessing folder
# Solution: Check folder permissions
ls -la /path/to/folder
chmod 755 /path/to/folder  # If needed
```

#### 2. Docker Image Not Found
```bash
# Error: Unable to find image 'mep-file-watcher:latest'
# Solution: Build the image
docker build -t mep-file-watcher:latest core/file_watcher/
```

#### 3. Network Connection Issues
```bash
# Error: Connection refused to processor
# Solution: Check if core processor is running
curl http://localhost:8001/health
```

#### 4. Folder Not Found
```bash
# Error: Folder does not exist
# Solution: Verify path and permissions
ls -la /path/to/folder
```

### Debug Mode

To see detailed Docker commands, add debug output to scripts:
```bash
# Add this line before eval $FULL_CMD in scripts
echo "Debug: $FULL_CMD"
```

## Performance Tips

### 1. Concurrency
- Use `--concurrent 10` for fast processing of many files
- Use `--concurrent 1` for memory-constrained systems

### 2. Recursive Scanning
- Use `--no-recursive` for top-level folders only
- Use `--max-depth 3` to limit scan depth

### 3. Dry Run
- Always use `--dry-run` first to preview what will be processed
- Check file counts and types before actual processing

### 4. Report Saving
- Use `--save-report` to save processing results
- Reports include success/error details for each file

## Integration with Existing System

### 1. File Watcher Service
The dynamic scripts work alongside the existing file watcher service:
- Existing service: Monitors `./watch_folder`
- Dynamic scripts: Monitor any folder on-demand

### 2. Processing Pipeline
All files processed by dynamic scripts go through the same pipeline:
- Text extraction
- Metadata processing
- Embedding generation
- Entity extraction
- Storage in all databases

### 3. Dashboard Integration
Processed files appear in the dashboard just like files from the regular watch folder.

## Examples

### Complete Workflow
```bash
# 1. Preview scan of external drive
./core/scan_folder_dynamic.sh /media/user/external_drive/documents --dry-run

# 2. Process all files
./core/scan_folder_dynamic.sh /media/user/external_drive/documents

# 3. Watch for new files
./core/watch_folder_dynamic.sh /media/user/external_drive/documents
```

### Batch Processing
```bash
# Process multiple folders
for folder in /path/to/folder1 /path/to/folder2 /path/to/folder3; do
    echo "Processing $folder..."
    ./core/scan_folder_dynamic.sh "$folder" --save-report "${folder##*/}_report.json"
done
```

### Scheduled Scanning
```bash
# Add to crontab for daily scanning
0 2 * * * /path/to/mep_ainabox/core/scan_folder_dynamic.sh /media/user/external_drive/documents
```

## Conclusion

The dynamic folder scanning system provides a flexible, secure, and efficient way to process files from any location on your system without modifying Docker configurations. It's perfect for:

- External drives and USB devices
- Network shares and cloud storage
- Temporary and download folders
- Batch processing workflows
- Automated scanning schedules

The system maintains all the security and processing capabilities of the original file watcher while providing the flexibility to work with any folder path. 