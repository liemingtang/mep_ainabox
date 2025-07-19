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

### Debug Commands
```bash
# Check all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check resource usage
docker stats

# View detailed logs
docker compose logs -f [service-name]

# Check service health
curl http://localhost:8010/api/admin/status
```

## 🔒 Security Considerations

### Network Security
- **Local Access Only**: Dashboard accessible only from localhost
- **No External Access**: No external network access by default
- **Service Isolation**: Dashboard runs separately from other services

### File Permissions
- **User Permissions**: Dashboard runs as current user
- **No Root Access**: No root privileges required
- **Secure File Access**: Proper file permissions maintained

### Environment Variables
- **Sensitive Data Masking**: API keys and passwords masked in logs
- **Secure Storage**: Environment variables stored securely
- **Access Control**: Limited access to sensitive configuration

### Production Recommendations
- **Authentication**: Add authentication to dashboard
- **Reverse Proxy**: Use reverse proxy with SSL
- **Access Control**: Implement role-based access control
- **Audit Logging**: Monitor dashboard access logs

## 📊 Performance Optimization

### Dashboard Performance
- **Caching**: Implement caching for static data
- **Connection Pooling**: Optimize database connections
- **Resource Limits**: Set appropriate resource limits
- **Log Rotation**: Implement log rotation and cleanup

### Monitoring Optimization
- **Health Check Frequency**: Adjust health check intervals
- **Metrics Collection**: Optimize metrics collection frequency
- **Log Levels**: Configure appropriate log levels
- **Resource Usage**: Monitor dashboard resource consumption

## 🔄 Development

### Adding New Features
1. **Backend Changes**: Modify `core/dashboard/main.py`
2. **Frontend Changes**: Update templates in `core/dashboard/templates/`
3. **Static Assets**: Add CSS/JS in `core/dashboard/static/`
4. **API Endpoints**: Add new API endpoints as needed

### Customization
- **UI Themes**: Customize dashboard appearance
- **Service Integration**: Add new service monitoring
- **Metrics**: Add custom metrics collection
- **Alerts**: Implement custom alerting

### Testing
```bash
# Test dashboard health
curl http://localhost:8010/api/health

# Test admin panel
curl http://localhost:8010/api/admin/status

# Test service endpoints
curl http://localhost:8010/api/services
```

## 📚 Integration

### External Monitoring
- **Prometheus**: Export metrics to Prometheus
- **Grafana**: Use Grafana for advanced visualization
- **Alerting**: Integrate with alerting systems
- **Log Aggregation**: Send logs to external systems

### API Integration
- **REST APIs**: Use dashboard APIs for external monitoring
- **Webhooks**: Configure webhooks for status updates
- **Automation**: Integrate with automation tools
- **Reporting**: Generate automated reports

## 🆘 Support

### Getting Help
1. **Check Logs**: Review `core/logs/dashboard.log`
2. **Verify Configuration**: Check environment variables
3. **Test Connectivity**: Verify network connectivity
4. **Check Permissions**: Ensure proper file permissions

### Documentation
- **Admin Startup Guide**: [ADMIN_STARTUP_GUIDE.md](ADMIN_STARTUP_GUIDE.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **API Documentation**: [core/api_documentation.md](core/api_documentation.md)
- **Architecture**: [README_architecture.md](README_architecture.md)

### Community
- **Issues**: Report issues with detailed information
- **Feature Requests**: Suggest new features
- **Contributions**: Contribute improvements
- **Questions**: Ask questions in discussions

---

The MEP AI NABOX dashboard provides a comprehensive monitoring and management interface for the entire system, making it easy to deploy, monitor, and maintain your AI-powered document processing system.

## 📝 Recent Updates

### Error Handling Improvements (Latest)
The dashboard has been enhanced with comprehensive error handling to provide a smooth user experience:

- **Service Unavailability**: Dashboard gracefully handles when backend services are not running
- **JavaScript Error Prevention**: Global error handlers prevent browser alerts
- **Data Validation**: All API responses are validated with safe fallback values
- **Graceful Degradation**: Dashboard continues functioning even when services are down
- **No Error Alerts**: Dashboard loads successfully without showing "Failed to load dashboard data" alerts
- **Auto-recovery**: Dashboard automatically updates when services become available

For detailed information about these improvements, see the [Changelog](CHANGELOG.md) and [Quick Reference](QUICK_REFERENCE.md) guides. 