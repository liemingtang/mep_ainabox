# Docker-based Folder Scanner

A containerized version of the batch folder scanner that can be run as a tool without requiring Python dependencies on the host system.

## 🐳 Docker Features

- **Self-contained environment** - All Python dependencies included
- **No host installation required** - Just Docker needed
- **Consistent execution** - Same environment everywhere
- **Easy deployment** - Can be run on any system with Docker
- **Security** - Runs as non-root user inside container

## 📦 Files

- `Dockerfile` - Container definition
- `build_docker.sh` - Build script for the Docker image
- `scan_folder.sh` - Convenient wrapper script
- `folder_scanner.py` - Main Python script
- `requirements.txt` - Python dependencies

## 🚀 Quick Start

### 1. Build the Docker Image
```bash
cd mep_ainabox/core/batch
./build_docker.sh
```

### 2. Use the Docker Scanner
```bash
# Basic usage
./scan_folder.sh /path/to/folder

# With options
./scan_folder.sh /path/to/folder --max-depth 3 --session-id my_scan

# Dry run (no database changes)
./scan_folder.sh /path/to/folder --dry-run
```

## 📋 Usage Examples

### Scan a documents folder
```bash
./scan_folder.sh /home/user/documents
```

### Scan with depth limit
```bash
./scan_folder.sh /home/user/projects --max-depth 2
```

### Test run without changes
```bash
./scan_folder.sh /home/user/documents --dry-run
```

### Custom session ID
```bash
./scan_folder.sh /home/user/documents --session-id backup_2024_01
```

## 🔧 Manual Docker Commands

If you prefer to run Docker commands directly:

```bash
# Basic usage
docker run --rm --network host \
  -v /path/to/folder:/scan \
  -v /path/to/config:/app/config \
  mep-folder-scanner:latest /scan

# With options
docker run --rm --network host \
  -v /path/to/folder:/scan \
  -v /path/to/config:/app/config \
  mep-folder-scanner:latest /scan --max-depth 3 --session-id my_scan

# Dry run
docker run --rm --network host \
  -v /path/to/folder:/scan \
  -v /path/to/config:/app/config \
  mep-folder-scanner:latest /scan --dry-run
```

## 🏗️ Docker Image Details

### Base Image
- `python:3.11-slim` - Lightweight Python 3.11

### System Dependencies
- `libmagic1` - File type detection
- `libpq-dev` - PostgreSQL client libraries
- `gcc` - Compilation support

### Python Dependencies
- `asyncpg` - Async PostgreSQL driver
- `PyYAML` - YAML configuration parsing
- `python-magic` - File type detection
- `pathlib2` - Path utilities

### Security
- Runs as non-root user (`scanner`)
- Minimal attack surface
- Read-only file system except for mounted volumes

## 🔄 Container Lifecycle

### Building
```bash
./build_docker.sh
```
- Downloads base Python image
- Installs system dependencies
- Installs Python packages
- Creates non-root user
- Sets up entrypoint

### Running
```bash
./scan_folder.sh /path/to/folder
```
- Mounts target folder to `/scan`
- Mounts config directory to `/app/config`
- Uses host networking for database access
- Executes scanner with provided arguments

### Cleanup
- Container is automatically removed after execution (`--rm`)
- No persistent state left on host
- Temporary files cleaned up

## 🌐 Network Configuration

The container uses `--network host` to:
- Access PostgreSQL on the host (localhost:5432)
- Use the same network as the host system
- Avoid port mapping complexity

## 📁 Volume Mounts

### Required Mounts
- **Target folder**: `-v /path/to/folder:/scan`
  - The folder to be scanned
  - Mounted as `/scan` inside container

- **Config directory**: `-v /path/to/config:/app/config`
  - Contains `main.yaml` with database configuration
  - Mounted as `/app/config` inside container

## 🔍 Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker
   sudo systemctl start docker
   ```

2. **Permission denied**
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

3. **Database connection failed**
   - Check PostgreSQL is running
   - Verify config file exists and is correct
   - Ensure host networking is working

4. **Folder not found**
   ```bash
   # Use absolute path
   ./scan_folder.sh $(realpath /path/to/folder)
   ```