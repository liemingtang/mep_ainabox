# MEP AI NABOX - System Initialization Guide

This guide explains how to initialize and manage the MEP AI NABOX system using the new initialization scripts.

## 🚀 Quick Start

For new installations, use the comprehensive initialization script:

```bash
./init_system.sh
```

This script will:
- Build all Docker images
- Start all infrastructure services
- Start all core services
- Start the dashboard
- Perform health checks

## 📋 Available Scripts

### 1. `init_system.sh` - Complete System Initialization
**Purpose**: Full system setup for new installations

**Usage**:
```bash
# Full initialization (recommended for new installs)
./init_system.sh

# Skip Docker build (if images already exist)
./init_system.sh --skip-build

# Skip service startup (build only)
./init_system.sh --skip-services

# Admin mode only (dashboard only)
./init_system.sh --admin-only
```

**What it does**:
- ✅ Checks Docker environment
- ✅ Creates necessary directories
- ✅ Sets proper permissions
- ✅ Loads environment variables
- ✅ Creates Docker network
- ✅ Builds all Docker images
- ✅ Starts infrastructure services
- ✅ Starts core services
- ✅ Starts dashboard
- ✅ Performs health checks
- ✅ Starts Qdrant UI

### 2. `stop_system.sh` - System Shutdown
**Purpose**: Gracefully stop all services

**Usage**:
```bash
./stop_system.sh
```

**What it does**:
- 🛑 Stops dashboard processes
- 🛑 Stops Qdrant UI processes
- 🛑 Stops all Docker containers
- 🧹 Cleans up PID files
- 🌐 Removes Docker network

### 3. `health_check.sh` - System Health Check
**Purpose**: Verify all services are running properly

**Usage**:
```bash
./health_check.sh
```

**What it checks**:
- 🔧 Infrastructure services (PostgreSQL, Elasticsearch, etc.)
- 🔧 Core services (API Gateway, Core Processor, etc.)
- 🎛️ UI services (Dashboard, Qdrant UI)
- 🌐 Service health endpoints
- 📊 System summary

## 🔄 Workflow Options

### Option 1: Complete Initialization (Recommended for New Installs)
```bash
# Initialize everything
./init_system.sh

# Check health
./health_check.sh

# When done
./stop_system.sh
```

### Option 2: Admin Mode (Dashboard Only)
```bash
# Start only dashboard for admin control
./start_admin.sh

# Use web interface to start other services
# Access: http://localhost:8010/admin
```

### Option 3: Incremental Startup
```bash
# Build images only
./init_system.sh --skip-services

# Start services later
cd services && docker compose up -d
cd ../core && docker compose up -d
```

## 🌐 Service URLs

After initialization, these services will be available:

### Core Services
- **Dashboard**: http://localhost:8010
- **Admin Panel**: http://localhost:8010/admin
- **API Gateway**: http://localhost:8000
- **Core Processor**: http://localhost:8001
- **Document Router**: http://localhost:8002
- **Processing Pipeline**: http://localhost:8003
- **Storage Manager**: http://localhost:8004

### Infrastructure Services
- **PostgreSQL**: localhost:5432
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **Qdrant**: http://localhost:6333
- **Neo4j Browser**: http://localhost:7474
- **Redis**: localhost:6379
- **MinIO Console**: http://localhost:9001
- **n8n**: http://localhost:5678
- **Flowise**: http://localhost:3001

## 📊 Monitoring Commands

```bash
# View all containers
docker ps

# View logs
docker compose logs -f

# Health check
./health_check.sh

# View dashboard logs
tail -f core/logs/dashboard.log

# View specific service logs
docker compose logs -f api-gateway
```

## 🔧 Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   sudo systemctl start docker
   ```

2. **Port conflicts**
   ```bash
   # Check what's using a port
   sudo netstat -tulpn | grep :8010
   
   # Kill process using port
   sudo kill -9 <PID>
   ```

3. **Permission issues**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 services/volumes/
   ```

4. **Build failures**
   ```bash
   # Clean and rebuild
   docker system prune -f
   ./init_system.sh
   ```

### Log Locations
- **Dashboard logs**: `core/logs/dashboard.log`
- **Docker logs**: `docker compose logs -f`
- **Service logs**: `services/logs/`

## 🎯 Best Practices

1. **For Development**:
   - Use `./start_admin.sh` for quick dashboard access
   - Start services incrementally as needed

2. **For Production**:
   - Use `./init_system.sh` for complete setup
   - Run `./health_check.sh` regularly
   - Monitor logs for issues

3. **For Testing**:
   - Use `./init_system.sh --skip-build` for faster restarts
   - Use `./stop_system.sh` to clean up completely

## 📝 Environment Configuration

The system uses environment files for configuration:

- **Core services**: `core/.env`
- **Infrastructure services**: `services/.env`

Copy from examples if they don't exist:
```bash
cp core/env.example core/.env
cp services/env.example services/.env
```

## 🚨 Important Notes

- The initialization script can take 10-20 minutes for new installations
- Docker images are large (several GB total)
- Ensure sufficient disk space (at least 10GB free)
- The system requires Docker and docker-compose
- All services use host networking for simplicity

## 📞 Support

If you encounter issues:

1. Run `./health_check.sh` to identify problems
2. Check logs: `tail -f core/logs/dashboard.log`
3. Verify Docker is running: `docker info`
4. Check disk space: `df -h`
5. Review the troubleshooting section above 