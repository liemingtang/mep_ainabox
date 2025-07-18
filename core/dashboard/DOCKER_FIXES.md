# Dashboard Docker Fixes

## Issues Identified

1. **Dashboard running outside Docker**: The dashboard was configured to run with `network_mode: "host"` which made it run outside the Docker network
2. **Configuration and logs tabs not working**: The dashboard was trying to access services via localhost instead of Docker service names
3. **No Docker access**: The dashboard couldn't access Docker commands to retrieve container logs

## Fixes Implemented

### 1. Docker Network Configuration

**Before:**
```yaml
dashboard:
  network_mode: "host"
  environment:
    - CORE_PROCESSOR_URL=http://localhost:8001
    - FILE_WATCHER_URL=http://localhost:8009
    # ... other localhost URLs
```

**After:**
```yaml
dashboard:
  ports:
    - "8010:8010"
  environment:
    - CORE_PROCESSOR_URL=http://core-processor:8001
    - FILE_WATCHER_URL=http://file-watcher:8009
    # ... other Docker service names
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./config:/app/config:ro
```

### 2. Service URL Updates

**Updated in `main.py`:**
- Changed all service URLs from `localhost` to Docker service names
- Updated `SERVICE_INFO` dictionary with correct Docker service URLs
- Updated `SERVICES` dictionary for health checks

**Examples:**
```python
# Before
"text-processor": "http://localhost:8005"
"api-gateway": "http://localhost:8000"

# After  
"text-processor": "http://text-processor:8005"
"api-gateway": "http://api-gateway:8000"
```

### 3. Docker CLI Installation

**Updated `Dockerfile`:**
```dockerfile
# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*
```

### 4. Docker Socket Access

**Added to docker-compose.yml:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

This allows the dashboard container to access Docker commands to retrieve logs from other containers.

### 5. Enhanced Logging

**Added debugging to `main.py`:**
```python
logger.info(f"Getting details for service: {service_name}")
logger.info(f"Health status for {service_name}: {health.status}")
logger.info(f"Retrieved {len(logs)} log lines for {service_name}")
logger.info(f"Retrieved {len(service_config)} configuration items for {service_name}")
```

## How to Apply the Fixes

### 1. Rebuild and Restart Dashboard

```bash
cd mep_ainabox/core
./restart_dashboard.sh
```

This script will:
- Stop the current dashboard container
- Remove the old container
- Rebuild the dashboard image with new changes
- Start the new container
- Verify the dashboard is running

### 2. Test the Dashboard

```bash
cd mep_ainabox/core/dashboard
python3 test_docker_dashboard.py
```

This will test:
- Dashboard health
- Docker container access
- File watcher service details
- Log retrieval
- Configuration retrieval

### 3. Manual Testing

Access the dashboard at:
- **Main Dashboard**: http://localhost:8010
- **File Watcher Details**: http://localhost:8010/service/file-watcher

## Expected Results

After applying the fixes:

1. **Dashboard runs in Docker**: The dashboard will be running inside a Docker container
2. **Configuration tab works**: Shows service-specific configuration, environment variables, and config files
3. **Logs tab works**: Shows real-time logs from Docker containers
4. **Metrics tab works**: Shows service metrics and Docker container stats
5. **All services accessible**: Dashboard can communicate with all other services via Docker network

## Troubleshooting

### Dashboard Not Starting

```bash
# Check dashboard logs
docker compose logs dashboard

# Check if Docker socket is accessible
docker compose exec dashboard docker ps
```

### Services Not Accessible

```bash
# Check if services are running
docker compose ps

# Test service connectivity from dashboard
docker compose exec dashboard curl http://core-processor:8001/health
```

### Configuration/Logs Not Loading

```bash
# Check dashboard API endpoints
curl http://localhost:8010/api/service/file-watcher/configuration
curl http://localhost:8010/api/service/file-watcher/logs

# Check dashboard logs for errors
docker compose logs dashboard
```

## Benefits

1. **Proper Docker Integration**: Dashboard runs as a proper Docker service
2. **Network Isolation**: Uses Docker network for service communication
3. **Container Log Access**: Can retrieve logs from all containers
4. **Configuration Access**: Can read configuration files from containers
5. **Metrics Collection**: Can collect Docker container statistics
6. **Security**: Proper container isolation and access controls

## Files Modified

1. **`docker-compose.yml`**: Updated dashboard service configuration
2. **`main.py`**: Updated service URLs and added debugging
3. **`Dockerfile`**: Added Docker CLI installation
4. **`restart_dashboard.sh`**: Created restart script
5. **`test_docker_dashboard.py`**: Created Docker-specific test script

The dashboard should now work properly when running in Docker with full access to logs, configuration, and metrics for all services. 