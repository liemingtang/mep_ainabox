# MEP AI NABOX - Dashboard Guide

This guide provides comprehensive information about the MEP AI NABOX dashboard system, including setup, usage, and troubleshooting.

## 🎯 Overview

The MEP AI NABOX dashboard is a web-based monitoring and management interface that provides:

- **Real-time System Monitoring**: Live status of all services
- **Service Management**: Start, stop, and monitor services
- **Log Streaming**: Real-time log viewing with syntax highlighting
- **Configuration Management**: Secure configuration viewing
- **Metrics Collection**: System and service metrics
- **Admin Panel**: Web-based service startup and management

## 🏗️ Architecture

### Host-Based Design
The dashboard runs directly on the host (not in Docker) for several advantages:

- **Better Performance**: Direct access to system resources
- **File System Access**: Can access local files and directories
- **Command Execution**: Can run shell scripts and Docker commands
- **Network Access**: Direct access to localhost services
- **Environment Variables**: Full access to host environment

### Technology Stack
- **Backend**: Python FastAPI
- **Frontend**: HTML/CSS/JavaScript with real-time updates
- **Templates**: Jinja2 templating engine
- **Logging**: Structured JSON logging
- **Monitoring**: Real-time health checks and metrics

### JavaScript Architecture and Error Handling

The dashboard's JavaScript implementation includes comprehensive error handling and reliability features:

#### Core Functions
- **`loadDashboardData()`**: Main data loading function with parallel API calls and error handling
- **`updateStatistics()`**: Updates dashboard statistics with safe property access
- **`updateServiceHealthSummary()`**: Updates service health counts with array validation
- **`updateDocumentsTable()`**: Updates documents table with comprehensive error handling
- **`updatePipelineStatus()`**: Updates pipeline status with container validation

#### Error Handling Features
- **Global Error Handlers**: Catch unhandled exceptions and promise rejections
- **HTTP Status Checking**: Validate API responses before processing
- **Safe Property Access**: Use optional chaining and fallback values
- **Array Validation**: Ensure arrays exist before processing
- **Individual Error Handling**: Each function has try-catch blocks
- **Console Logging**: Detailed warnings for debugging without user alerts

#### Data Flow
1. **Initial Load**: Dashboard loads with fallback values
2. **API Calls**: Parallel requests to `/api/stats`, `/api/health`, `/api/documents`
3. **Error Handling**: Each API call has individual error handling
4. **Data Validation**: Responses are validated before processing
5. **UI Updates**: Safe updates to DOM elements with fallback values
6. **Auto-refresh**: Continuous updates every 30 seconds with error handling

#### Service Unavailability Handling
When backend services are not running:
- API calls return default values instead of throwing errors
- Dashboard displays appropriate "empty state" messages
- No browser error alerts are shown
- Console warnings provide debugging information
- Auto-refresh continues without interruption

## 🚀 Getting Started

### Quick Start
```bash
cd mep_ainabox
./start_admin.sh
```

This will:
1. Start the dashboard on http://localhost:8010
2. Provide access to the admin panel at http://localhost:8010/admin
3. Allow you to start all services through the web interface

### Manual Dashboard Control
```bash
# Start dashboard in foreground
cd core && ./start_dashboard_host.sh

# Start dashboard in background
cd core && ./start_dashboard_host.sh --background

# Stop dashboard
cd core && ./stop_dashboard_host.sh
```

## 📊 Dashboard Features

### Main Dashboard (http://localhost:8010)

#### System Overview
- **Service Status**: Real-time status of all services
- **Health Indicators**: Color-coded health status
- **Quick Actions**: Direct links to service details
- **System Statistics**: Overview of system performance

#### Service Categories
1. **Infrastructure Services**
   - PostgreSQL, Elasticsearch, Qdrant, Neo4j, Redis, MinIO
   - Management UIs: Kibana, pgAdmin, Redis Commander, MinIO Console
   - Automation tools: n8n, Flowise

2. **Core System Services**
   - API Gateway, Core Processor, Document Router
   - Processing Pipeline, Storage Manager
   - Text/Metadata/Embedding/Entity Processors
   - File Watcher

#### Navigation
- **Dashboard**: Main system overview
- **Admin Panel**: Service management interface
- **Service Details**: Individual service monitoring
- **Logs**: Real-time log streaming
- **Configuration**: System configuration viewing

### Admin Panel (http://localhost:8010/admin)

#### Service Management
- **Start All Services**: One-click startup of all services
- **Real-time Progress**: Visual progress bar and detailed logs
- **Status Monitoring**: Live updates every 5 seconds
- **Error Handling**: Automatic error detection and highlighting

#### Startup Process
1. **Infrastructure Services** (2-3 minutes)
   - Database services and management UIs
   - Automation and workflow tools

2. **Core System Services** (2-3 minutes)
   - Processing and storage services
   - File monitoring and API services

3. **Health Verification** (1-2 minutes)
   - Service health checks
   - Connection verification

#### Real-time Features
- **Terminal-style Logs**: Real-time startup logs with color coding
- **Progress Tracking**: Visual progress bar
- **Auto-scroll**: Automatic scrolling to latest logs
- **Error Highlighting**: Automatic error detection

### Scan Folder Management (http://localhost:8010/scan-folder)

#### Overview
The scan folder feature provides a comprehensive interface for processing documents from any folder on your system. This feature has been recently enhanced with improved file path handling and error resolution.

#### Key Features

##### 1. Folder Selection and Preview
- **Folder Browser**: Interactive folder selection with path validation
- **Path Input**: Manual path entry with validation
- **Folder Preview**: View folder structure before processing
- **File Statistics**: See total files, supported formats, and sizes
- **Accessibility Check**: Verify folder permissions and accessibility

##### 2. Processing Configuration
- **Processing Mode**: Choose between queue-based or synchronous processing
- **Concurrency Control**: Set number of concurrent processing tasks (1-20)
- **Recursive Scanning**: Enable/disable subdirectory scanning
- **Depth Limiting**: Control maximum scanning depth (1-10 levels)
- **Report Generation**: Save detailed processing reports

##### 3. Real-time Monitoring
- **Live Progress**: Real-time updates on file processing
- **Execution Status**: Track running, completed, failed, or stopped executions
- **Detailed Logs**: View comprehensive execution logs
- **Error Reporting**: Detailed error messages with recovery suggestions

##### 4. Execution Management
- **Execution History**: View all past scan operations
- **Execution Details**: Detailed information about each execution
- **Log Streaming**: Real-time log output from running executions
- **Execution Control**: Stop running executions if needed

#### Recent Improvements (Latest Update)

##### File Path Handling Fixes
- **Fixed f-string formatting** in processing pipeline for proper variable interpolation
- **Enhanced path conversion** between host and container paths
- **Improved original file path tracking** for better data source management
- **Added environment variable support** for host path mapping (`HOST_SCAN_FOLDER_PATH`)

##### Error Resolution
- **Resolved "File not found" errors** that were occurring in the processing pipeline
- **Fixed container path conversion** issues when scanning external folders
- **Improved error handling** for external folder access and permissions
- **Enhanced logging** for better debugging and troubleshooting

#### Usage Workflow

1. **Access Scan Folder Page**
   - Navigate to http://localhost:8010/scan-folder
   - Or click "Scan Folder" from the admin panel

2. **Select Folder**
   - Use folder browser to select a folder (recommended)
   - Or manually enter the absolute path
   - Ensure the folder is accessible and contains supported files

3. **Configure Processing**
   - Choose processing mode (queue-based recommended)
   - Set concurrency level based on system resources
   - Configure recursive scanning and depth limits
   - Enable report generation if needed

4. **Preview Folder (Optional)**
   - Click "Preview Folder" to see folder structure
   - Review file statistics and supported formats
   - Verify folder accessibility before processing

5. **Start Processing**
   - Click "Start Scan" to begin processing
   - Monitor real-time progress and logs
   - Track execution status and completion

6. **Monitor Results**
   - View processing results in real-time
   - Check execution logs for detailed information
   - Review any errors or warnings

#### Supported File Types
- **Documents**: PDF, DOCX, DOC, TXT, HTML, HTM
- **Images**: PNG, JPG, JPEG, GIF, BMP, TIFF
- **Spreadsheets**: CSV, XLSX, XLS

#### Best Practices

##### Folder Selection
- **Use absolute paths** for reliable folder access
- **Check folder permissions** before processing
- **Verify folder accessibility** from the container environment
- **Use preview mode** for large folders to estimate processing time

##### Processing Configuration
- **Start with queue-based processing** for better reliability
- **Adjust concurrency** based on system resources (5-10 recommended)
- **Use recursive scanning** for complete folder processing
- **Set appropriate depth limits** to avoid processing too many subdirectories

##### Monitoring and Troubleshooting
- **Monitor system resources** during processing
- **Check execution logs** for detailed progress information
- **Review error messages** for troubleshooting guidance
- **Use execution history** to track processing patterns

#### Command Line Alternative
For advanced users, the scan folder functionality is also available via command line:

```bash
# Basic scan with Docker
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder --queue

# Advanced scan with options
docker run --rm --network host \
  -v /path/to/folder:/app/scan_folder:ro \
  -e CORE_PROCESSOR_URL=http://localhost:8001 \
  -e HOST_SCAN_FOLDER_PATH=/path/to/folder \
  mep-file-watcher:latest \
  python3 /app/folder_scanner.py /app/scan_folder \
  --queue --max-depth 3 --concurrent 10 --save-report report.json
```

#### Troubleshooting Scan Folder Issues

##### Common Problems and Solutions

**"Folder not found" or "Permission denied"**
- Verify the folder path is absolute and correct
- Check folder permissions and accessibility
- Ensure the folder exists and is readable

**"File not found" errors during processing**
- This issue has been resolved in the latest update
- Ensure you're using the updated file watcher container
- Check that the `HOST_SCAN_FOLDER_PATH` environment variable is set correctly

**Processing pipeline errors**
- Verify all services are running (core processor, processing pipeline)
- Check service logs for detailed error information
- Ensure Docker is running for container-based processing

**Slow processing or timeouts**
- Reduce concurrency level to decrease system load
- Check system resources (CPU, memory, disk I/O)
- Use preview mode to estimate processing requirements

## 🔧 API Endpoints

### Dashboard APIs
```bash
# System health
GET /api/health

# System statistics
GET /api/stats

# Service status overview
GET /api/services

# Admin panel status
GET /api/admin/status

# Start all services
POST /api/admin/start-services

# Get startup logs
GET /api/admin/startup-logs
```

### Service-specific APIs
```bash
# Service details
GET /service/{service_name}

# Service logs
GET /api/service/{service_name}/logs

# Service metrics
GET /api/service/{service_name}/metrics

# Service configuration
GET /api/service/{service_name}/configuration
```

### Health Check APIs
```bash
# Individual service health
GET /api/health/{service_name}

# Database connectivity
GET /api/health/database

# Network connectivity
GET /api/health/network
```

### Scan Folder APIs
```bash
# Start scan folder execution
POST /api/scan-folder/start
Content-Type: application/json
{
  "folder_path": "/path/to/folder",
  "processing_mode": "queue",
  "concurrent_limit": 5,
  "max_depth": 10,
  "recursive": true,
  "save_report": false
}

# Get scan folder executions
GET /api/scan-folder/executions

# Get execution details
GET /api/scan-folder/executions/{execution_id}

# Get execution logs
GET /api/scan-folder/executions/{execution_id}/logs

# Stop execution
POST /api/scan-folder/executions/{execution_id}/stop

# Preview folder structure
POST /api/scan-folder/preview
Content-Type: application/json
{
  "folder_path": "/path/to/folder",
  "recursive": true,
  "max_depth": 10
}
```

## 📈 Monitoring Features

### Real-time Monitoring
- **Service Status**: Live status updates every 5 seconds
- **Health Checks**: Automatic health verification
- **Resource Usage**: CPU, memory, and disk usage
- **Network Connectivity**: Port and service connectivity

### Log Management
- **Real-time Logs**: Live log streaming from all services
- **Syntax Highlighting**: Color-coded log output
- **Log Filtering**: Filter by service, level, or time
- **Log Search**: Search through log content

### Metrics Collection
- **Docker Stats**: Container resource usage
- **Service Metrics**: Application-level metrics
- **System Metrics**: Host system performance
- **Custom Metrics**: Application-specific measurements

### Configuration Management
- **Secure Viewing**: Sensitive data masking
- **Configuration Groups**: Organized by category
- **Environment Variables**: Host and container environment
- **Service Configs**: Individual service configurations

## 🛠️ Service Details

### Individual Service Pages
Each service has a dedicated page with:

#### Status Information
- **Current Status**: Running, stopped, or error
- **Health Status**: Healthy, unhealthy, or unknown
- **Uptime**: Service uptime and restart information
- **Version**: Service version and build information

#### Monitoring Data
- **Real-time Logs**: Live log streaming
- **Metrics**: Performance and resource metrics
- **Configuration**: Current configuration settings
- **Dependencies**: Service dependencies and connections

#### Management Actions
- **Start/Stop**: Service control actions
- **Restart**: Service restart functionality
- **Log Download**: Download log files
- **Configuration Edit**: Edit service configuration

## 🔍 Troubleshooting

### Common Dashboard Issues

#### Dashboard Error Handling and Reliability
The dashboard has been enhanced with comprehensive error handling to provide a smooth user experience even when backend services are not running:

**Automatic Error Recovery**:
- **Service Unavailability**: Dashboard gracefully handles when services (Elasticsearch, Qdrant, Core Processor) are not running
- **API Failures**: HTTP errors are caught and handled without showing browser alerts
- **Data Validation**: All API responses are validated before processing
- **Fallback Values**: Default values (0s, empty arrays) are used when data is unavailable

**JavaScript Error Prevention**:
- **Global Error Handlers**: Unhandled JavaScript exceptions are caught and logged
- **Promise Rejection Handling**: Unhandled promise rejections are prevented from showing alerts
- **Safe Property Access**: All object properties are accessed safely with fallback values
- **Array Validation**: All arrays are validated before processing

**Expected Behavior When Services Are Down**:
- Dashboard loads successfully without error alerts
- Statistics show zero values (0 documents, 0 services)
- Service health shows all services as unavailable
- Documents table shows "No documents found"
- Pipeline status shows services as "unknown" or "error"
- Console warnings are logged for debugging (not user-facing)

#### Dashboard Not Starting
```bash
# Check if port 8010 is available
netstat -tulpn | grep 8010

# Check if Python process is running
pgrep -f "python3.*main.py"

# Check dashboard logs
tail -f core/logs/dashboard.log

# Restart dashboard
cd core && ./stop_dashboard_host.sh && ./start_dashboard_host.sh --background
```

#### Template Not Found Errors
```bash
# Ensure dashboard is running from correct directory
cd core/dashboard && python3 main.py

# Check template files exist
ls -la templates/

# Verify working directory
pwd
```

#### Permission Errors
```bash
# Fix permissions
sudo chown -R $USER:$USER mep_ainabox/
chmod +x start_admin.sh
chmod +x core/start_dashboard_host.sh
chmod +x core/stop_dashboard_host.sh
```

#### Environment Variable Issues
```bash
# Check .env files exist
ls -la core/.env
ls -la services/.env

# Verify environment loading
cd core && source .env && echo $POSTGRES_HOST
```

#### Network Connectivity Issues
```bash
# Check Docker network
docker network ls | grep mep-services-network

# Test localhost connectivity
curl http://localhost:8000/health

# Check service ports
netstat -tulpn | grep -E ":(8000|8001|8009|5432|9200|6333)"
```