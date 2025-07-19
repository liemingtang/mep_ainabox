# MEP AI NABOX - Admin Startup Guide

This guide explains how to use the **Admin Startup Mode** for MEP AI NABOX, which provides a web-based interface to manage and monitor all services.

## 🎯 Overview

The Admin Startup Mode allows you to:
1. **Start only the dashboard first** - Quick initial startup
2. **Use a web interface** to start all other services
3. **Monitor startup progress** in real-time with logs
4. **Control service management** through a modern admin panel

## 🛑 Stopping the System

### Complete System Shutdown
To completely shut down all services and clean up all processes:

```bash
cd mep_ainabox
./stop_admin.sh
```

This script will:
1. **Stop Dashboard Service** - Terminates the host-based dashboard
2. **Stop Python Processes** - Kills all Python main.py processes
3. **Stop Core Services** - Shuts down all core system Docker containers
4. **Stop Infrastructure Services** - Shuts down all infrastructure Docker containers
5. **Stop Development Services** - Shuts down development UIs (pgAdmin, Redis Commander, etc.)
6. **Stop Monitoring Services** - Shuts down Prometheus and Grafana
7. **Clean Up Containers** - Removes any remaining MEP containers
8. **Final Cleanup** - Kills any remaining related processes
9. **Verification** - Confirms all services are stopped

### Manual Stop Commands (Alternative)
If you prefer to stop services manually:

```bash
# Stop core services
cd mep_ainabox/core
docker compose down

# Stop infrastructure services
cd ../services
docker compose down
docker compose --profile dev down
docker compose --profile monitoring down

# Stop dashboard
cd ../core
pkill -f "python.*dashboard.*main.py"

# Stop all Python processes
pkill -f "python.*main.py"
```

## 🚀 Quick Start

### Step 1: Start Admin Mode
```bash
cd mep_ainabox
./start_admin.sh
```

This will:
- ✅ Start only the dashboard service on the host (not in Docker)
- ✅ Set up the Docker network
- ✅ Create necessary directories
- ✅ Load environment variables
- ✅ Verify dashboard is ready

### Step 2: Access Admin Panel
Open your browser and go to:
- **Dashboard**: http://localhost:8010
- **Admin Panel**: http://localhost:8010/admin

### Step 3: Start All Services
1. Click the **"Start All Services"** button in the admin panel
2. Watch the real-time startup progress
3. Monitor logs and status updates
4. Wait for completion (typically 5-10 minutes)

## 🎛️ Admin Panel Features

### Status Overview
- **Infrastructure Status**: PostgreSQL, Elasticsearch, Qdrant, Redis, MinIO
- **Core System Status**: API Gateway, Core Processor, File Watcher, etc.
- **Startup Status**: Current startup progress
- **Last Update**: Real-time status updates

### Service Control
- **Start All Services**: One-click startup of infrastructure and core services
- **Stop All Services**: One-click shutdown of all services with confirmation
- **Real-time Progress**: Visual progress bar and detailed logs for both startup and shutdown
- **Status Monitoring**: Live updates every 5 seconds

### Log Monitoring
- **Terminal-style logs**: Real-time startup logs with color coding
- **Progress tracking**: Visual progress bar
- **Error highlighting**: Automatic error detection and highlighting
- **Auto-scroll**: Automatic scrolling to latest logs

## 📊 Admin Panel Interface

### Main Dashboard
```
┌─────────────────────────────────────────────────────────┐
│                    MEP AI NABOX Admin Panel              │
├─────────────────────────────────────────────────────────┤
│  Infrastructure: ● Running    Core System: ● Running     │
│  Startup Status: ○ Idle       Last Update: 14:30:25     │
├─────────────────────────────────────────────────────────┤
│  [🚀 Start All Services]  [🛑 Stop All Services]        │
├─────────────────────────────────────────────────────────┤
│  📦 Infrastructure Services: ● Running                   │
│  🔧 Core System Services: ● Running                      │
└─────────────────────────────────────────────────────────┘
```

### Startup Progress View
```
┌─────────────────────────────────────────────────────────┐
│  🔄 Startup Progress                                     │
│  ████████████████████████████████████████████████████ 100% │
├─────────────────────────────────────────────────────────┤
│  [14:30:01] 🚀 Starting MEP AI NABOX services...        │
│  [14:30:02] 📦 Starting infrastructure services...      │
│  [14:30:15] ✅ Infrastructure services started           │
│  [14:30:16] ⏳ Waiting for services to be ready...       │
│  [14:30:45] 🔧 Starting core system services...         │
│  [14:31:00] ✅ Core system services started              │
│  [14:31:01] 🎉 MEP AI NABOX startup completed!          │
└─────────────────────────────────────────────────────────┘
```

### Shutdown Progress View
```
┌─────────────────────────────────────────────────────────┐
│  🛑 Shutdown Progress                                    │
│  ████████████████████████████████████████████████████ 100% │
├─────────────────────────────────────────────────────────┤
│  [14:35:01] 🛑 Stopping MEP AI NABOX services...        │
│  [14:35:02] 🔧 Stopping core system services...          │
│  [14:35:05] ✅ Core system services stopped              │
│  [14:35:06] 📦 Stopping infrastructure services...       │
│  [14:35:10] ✅ Infrastructure services stopped           │
│  [14:35:11] 🔍 Performing final status checks...         │
│  [14:35:12] 🎉 MEP AI NABOX shutdown completed!         │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Technical Details

### Dashboard Architecture
- **Host-based Dashboard**: Runs directly on the host (not in Docker)
- **Python FastAPI**: Modern web framework for the dashboard
- **Real-time Updates**: WebSocket-like polling for live status
- **Template System**: Jinja2 templates for dynamic HTML generation

### Startup Process
1. **Infrastructure Services** (2-3 minutes)
   - PostgreSQL, Elasticsearch, Qdrant, Neo4j, Redis, MinIO
   - Management UIs: Kibana, pgAdmin, Redis Commander, MinIO Console
   - Automation tools: n8n, Flowise

2. **Core System Services** (2-3 minutes)
   - API Gateway, Core Processor, Document Router
   - Processing Pipeline, Storage Manager
   - Text/Metadata/Embedding/Entity Processors
   - File Watcher

3. **Health Checks** (1-2 minutes)
   - Verify all services are responding
   - Check database connections
   - Validate API endpoints

### Admin API Endpoints
- `GET /api/admin/status` - Get current admin status
- `POST /api/admin/start-services` - Start all services
- `POST /api/admin/stop-services` - Stop all services
- `GET /api/admin/startup-logs` - Get startup logs
- `GET /api/admin/shutdown-logs` - Get shutdown logs

### Service Detection
The admin panel automatically detects:
- **Infrastructure services** by checking ports: 5432, 9200, 6333, 6379
- **Core services** by checking ports: 8000, 8001, 8009
- **Startup progress** by monitoring background processes

## 🌐 Access URLs After Startup

### Core Application
- **Dashboard**: http://localhost:8010
- **API Gateway**: http://localhost:8000
- **Admin Panel**: http://localhost:8010/admin

### Infrastructure Services
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **Qdrant**: http://localhost:6333
- **Neo4j Browser**: http://localhost:7474
- **MinIO Console**: http://localhost:9001
- **Redis Commander**: http://localhost:8081
- **pgAdmin**: http://localhost:8080
- **n8n**: http://localhost:5678
- **Flowise**: http://localhost:3001

## 🛠️ Management Commands

### Admin Mode Commands
```bash
# Start admin mode
./start_admin.sh

# Check dashboard status
curl http://localhost:8010/api/health

# Check admin status
curl http://localhost:8010/api/admin/status

# View dashboard logs
tail -f core/logs/dashboard.log

# Stop dashboard
cd core && ./stop_dashboard_host.sh
```

### Manual Dashboard Control
```bash
# Start dashboard manually (foreground)
cd core && ./start_dashboard_host.sh

# Start dashboard manually (background)
cd core && ./start_dashboard_host.sh --background

# Stop dashboard manually
cd core && ./stop_dashboard_host.sh
```

### Traditional Commands (Alternative)
```bash
# Start all services traditionally
cd services && ./scripts/start-services.sh
cd ../core && ./start.sh

# Stop all services
cd core && docker compose down
cd ../services && docker compose down
```

## 🔍 Troubleshooting

### Common Issues

1. **Dashboard not starting**
   ```bash
   # Check if port 8010 is available
   netstat -tulpn | grep 8010
   
   # Check if Python process is running
   pgrep -f "python3.*main.py"
   
   # Restart dashboard
   cd core && ./stop_dashboard_host.sh && ./start_dashboard_host.sh --background
   ```

2. **Services directory not found**
   - The dashboard now runs on the host and can access all directories
   - Paths are automatically resolved to the correct project structure
   - No more Docker container path issues

3. **Template not found errors**
   - Ensure dashboard is running from the correct directory
   - Check that templates exist in `core/dashboard/templates/`
   - Restart the dashboard if needed

4. **Permission errors**
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER mep_ainabox/
   chmod +x start_admin.sh
   chmod +x core/start_dashboard_host.sh
   chmod +x core/stop_dashboard_host.sh
   ```

5. **Network issues**
   ```bash
   # Check Docker network
   docker network ls | grep mep-services-network
   
   # Recreate network if needed
   docker network create mep-services-network
   ```

6. **Environment variable issues**
   - Check that `.env` files exist in both `core/` and `services/` directories
   - Ensure proper environment variable loading in startup scripts

## 📋 System Requirements

### Prerequisites
- **Python 3.8+**: Required for the dashboard
- **Docker & Docker Compose**: For running services
- **Git**: For cloning the repository
- **Linux/macOS**: Tested on Ubuntu 20.04+

### Disk Space
- **Minimum**: 10GB free space
- **Recommended**: 50GB+ for production use

### Memory
- **Minimum**: 4GB RAM
- **Recommended**: 8GB+ RAM for optimal performance

## 🔒 Security Considerations

### Network Security
- Dashboard runs on localhost only (127.0.0.1)
- No external network access by default
- Use reverse proxy for external access if needed

### File Permissions
- Dashboard runs as the current user
- No root privileges required
- Proper file permissions maintained

### Environment Variables
- Sensitive data stored in `.env` files
- API keys and passwords masked in logs
- Secure credential management

## 📈 Performance Monitoring

### Dashboard Metrics
- **Response Time**: Real-time service health checks
- **Service Status**: Live status of all components
- **Resource Usage**: CPU and memory monitoring
- **Error Tracking**: Automatic error detection and logging

### Log Management
- **Dashboard Logs**: `core/logs/dashboard.log`
- **Service Logs**: Individual service logs in respective directories
- **Startup Logs**: Real-time startup progress tracking
- **Error Logs**: Detailed error reporting and debugging

## 🚀 Advanced Features

### Custom Configuration
- Modify `core/dashboard/main.py` for custom dashboard features
- Update templates in `core/dashboard/templates/` for UI changes
- Configure service endpoints in environment variables

### Integration Options
- **API Integration**: Use dashboard APIs for external monitoring
- **Webhook Support**: Configure webhooks for status updates
- **Metrics Export**: Export metrics to external monitoring systems

### Scaling Considerations
- **Horizontal Scaling**: Run multiple dashboard instances
- **Load Balancing**: Use reverse proxy for multiple instances
- **Database Scaling**: Configure external databases for persistence

---

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs in `core/logs/dashboard.log`
3. Check service-specific logs in their respective directories
4. Verify all prerequisites are met

The Admin Startup Mode provides a modern, user-friendly way to manage your MEP AI NABOX deployment with real-time monitoring and control capabilities. 