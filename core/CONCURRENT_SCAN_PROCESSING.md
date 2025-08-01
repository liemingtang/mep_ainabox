# Concurrent Scan Folder Processing

## Overview

The system now supports concurrent processing of multiple local folders using a shared Docker volume approach with unique folder naming. This allows multiple scan operations to run simultaneously without conflicts.

## How It Works

### 1. Shared Volume Architecture

- **Shared Volume**: `shared_scan_folders` - A Docker volume accessible by all processing services
- **Mount Point**: `/app/scan_folders` - Where all services can access mounted folders
- **Unique Naming**: Each folder gets a unique name to prevent conflicts

### 2. Unique Folder Naming

Each mounted folder gets a unique name following this pattern:
```
{folder_name}_{path_hash}_{timestamp}
```

Example:
- `/media/lie/DATA2/ai_scan_folder` → `ai_scan_folder_a1b2c3d4_123456`
- `/home/user/documents` → `documents_e5f6g7h8_789012`

### 3. Concurrent Processing Flow

1. **Scan Request**: User initiates scan of a local folder
2. **Volume Mounting**: System mounts the folder to shared volume with unique name
3. **File Processing**: All processing services access files via shared volume
4. **Cleanup**: Old folders are automatically cleaned up after processing

## Key Features

### ✅ Concurrent Safety
- **Unique Names**: No conflicts between different folders with same name
- **Retry Logic**: Automatic retry with exponential backoff for mount failures
- **Atomic Operations**: Safe concurrent mounting/unmounting

### ✅ Automatic Cleanup
- **Age-based Cleanup**: Old folders automatically removed after 24 hours
- **Manual Cleanup**: CLI command to clean up old folders
- **Volume Management**: Prevents volume bloat over time

### ✅ Service Integration
- **All Services**: Text processor, metadata processor, embedding processor, etc.
- **Shared Access**: All services can access any mounted folder
- **Dynamic Discovery**: Services automatically find files in shared volume

## Usage Examples

### Mount a Folder
```bash
# Mount a folder with automatic unique naming
python3 volume_manager.py mount --path /media/lie/DATA2/ai_scan_folder

# Mount with custom name
python3 volume_manager.py mount --path /home/user/documents --name my_docs
```

### List Mounted Folders
```bash
python3 volume_manager.py list
```

### Unmount a Folder
```bash
python3 volume_manager.py unmount --name ai_scan_folder_a1b2c3d4_123456
```

### Cleanup Old Folders
```bash
# Clean up folders older than 24 hours (default)
python3 volume_manager.py cleanup

# Clean up folders older than 12 hours
python3 volume_manager.py cleanup --max-age 12
```

## Concurrent Processing Scenarios

### Scenario 1: Multiple Users
```
User A scans: /media/user1/documents
User B scans: /media/user2/documents  
User C scans: /home/user3/backup

Result:
- documents_a1b2c3d4_123456 (User A)
- documents_e5f6g7h8_789012 (User B) 
- backup_i9j0k1l2_345678 (User C)
```

### Scenario 2: Same Folder, Different Times
```
Time 1: Scan /media/lie/DATA2/ai_scan_folder
Time 2: Scan /media/lie/DATA2/ai_scan_folder (new files added)

Result:
- ai_scan_folder_a1b2c3d4_123456 (Time 1)
- ai_scan_folder_a1b2c3d4_789012 (Time 2)
```

### Scenario 3: Network Folders
```
Scan 1: /mnt/network/share1/documents
Scan 2: /mnt/network/share2/documents
Scan 3: /mnt/network/share3/documents

Result:
- documents_a1b2c3d4_123456 (Share 1)
- documents_e5f6g7h8_789012 (Share 2)
- documents_i9j0k1l2_345678 (Share 3)
```

## Technical Implementation

### Volume Manager Class
```python
class VolumeManager:
    def mount_folder_concurrent(self, host_path, folder_name=None, max_retries=3)
    def unmount_folder(self, folder_name)
    def list_mounted_folders(self)
    def cleanup_old_folders(self, max_age_hours=24)
```

### Processing Pipeline Integration
```python
# In processing_pipeline/main.py
volume_manager = VolumeManager()
unique_folder_name = volume_manager.mount_folder_concurrent(host_folder_path, folder_name)
file_path = f"/app/scan_folders/{unique_folder_name}/{filename}"
```

### Text Processor Integration
```python
# In text_processor/main.py
def get_shared_volume_path(container_path):
    # Try to find file in any mounted folder
    for folder_name in self._get_mounted_folders():
        shared_path = f"/app/scan_folders/{folder_name}/{filename}"
        if Path(shared_path).exists():
            return shared_path
```

## Benefits

1. **Scalability**: Handle multiple concurrent scan operations
2. **Reliability**: Automatic retry and conflict resolution
3. **Efficiency**: Shared access across all processing services
4. **Maintainability**: Automatic cleanup prevents resource bloat
5. **Flexibility**: Works with any local folder without configuration

## Testing

Run the concurrent processing test:
```bash
python3 test_concurrent_scan.py
```

This will test:
- Concurrent folder mounting
- File access from shared volume
- CLI commands
- Cleanup operations

## Monitoring

### Check Mounted Folders
```bash
python3 volume_manager.py list
```

### Monitor Volume Usage
```bash
docker volume inspect shared_scan_folders
```

### Cleanup Old Folders
```bash
python3 volume_manager.py cleanup --max-age 6
```

## Troubleshooting

### Common Issues

1. **Mount Failures**: Check Docker permissions and volume existence
2. **File Not Found**: Verify folder is properly mounted in shared volume
3. **Volume Full**: Run cleanup to remove old folders
4. **Permission Errors**: Ensure Docker has access to host folders

### Debug Commands

```bash
# Check volume exists
docker volume ls | grep shared_scan_folders

# Inspect volume contents
docker run --rm -v shared_scan_folders:/dest alpine ls -la /dest

# Check container access
docker exec mep-text-processor ls -la /app/scan_folders
``` 