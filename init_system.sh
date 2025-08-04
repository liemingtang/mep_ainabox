#!/bin/bash

# MEP AI NABOX - Complete System Initialization Script
# This script builds all Docker images and starts all services for new installations
# Usage: ./init_system.sh [--skip-build] [--skip-services] [--admin-only]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to show help
show_help() {
    echo "MEP AI NABOX - Complete System Initialization Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script builds all Docker images and starts all services for new installations."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help              Show this help message"
    echo "  --skip-build            Skip Docker image building (use existing images)"
    echo "  --skip-services         Skip service startup (build images only)"
    echo "  --admin-only            Start only the dashboard (admin mode)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                      # Full initialization (recommended for new installs)"
    echo "  $0 --skip-build         # Skip building images (faster restart)"
    echo "  $0 --skip-services      # Build images only, don't start services"
    echo "  $0 --admin-only         # Start only dashboard for admin control"
    echo ""
    echo "SERVICES:"
    echo "  Infrastructure: PostgreSQL, Elasticsearch, Kibana, Qdrant, Neo4j, Redis, MinIO, n8n, Flowise"
    echo "  Core: API Gateway, Core Processor, Document Router, Processing Pipeline, Storage Manager, File Watcher"
    echo "  UI: Dashboard (http://localhost:8010), Qdrant UI"
    echo ""
    echo "For more information, see INITIALIZATION_GUIDE.md"
}

# Parse command line arguments
SKIP_BUILD=false
SKIP_SERVICES=false
ADMIN_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        --admin-only)
            ADMIN_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 MEP AI NABOX - Complete System Initialization${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "core/docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: core/docker-compose.yml not found. Please run this script from the mep_ainabox root directory.${NC}"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Error: docker-compose is not installed or not in PATH${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Error: Docker daemon is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker environment check passed${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p core/{documents,processed,temp,logs,watch_folder,config}
mkdir -p core/cache/huggingface
mkdir -p services/{volumes,config,logs}
mkdir -p services/volumes/{postgres,elasticsearch,kibana,qdrant,neo4j,redis,minio,n8n,flowise,pgadmin,prometheus,grafana}
mkdir -p services/config/{postgres,elasticsearch,kibana,qdrant,neo4j,redis,minio}

# Set proper permissions
echo -e "${BLUE}🔐 Setting proper permissions...${NC}"
chmod -R 755 core/{documents,processed,temp,logs,watch_folder,cache} 2>/dev/null || true
sudo chown -R 1000:1000 services/volumes/elasticsearch 2>/dev/null || true
sudo chown -R 1000:1000 services/volumes/neo4j 2>/dev/null || true
sudo chown -R 1000:1000 services/volumes/redis 2>/dev/null || true
sudo chown -R 1000:1000 services/volumes/minio 2>/dev/null || true

# Load environment variables
echo -e "${BLUE}📋 Loading environment variables...${NC}"

# Load core environment variables
if [ -f "core/.env" ]; then
    echo "Loading core environment variables..."
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < core/.env
else
    echo -e "${YELLOW}⚠️  core/.env file not found. Using default values.${NC}"
fi

# Load services environment variables
if [ -f "services/.env" ]; then
    echo "Loading services environment variables..."
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < services/.env
else
    echo -e "${YELLOW}⚠️  services/.env file not found. Using default values.${NC}"
fi

# Create Docker network
echo -e "${BLUE}🌐 Setting up Docker network...${NC}"
if ! docker network ls | grep -q "mep-services-network"; then
    echo "Creating mep-services-network..."
    docker network create mep-services-network
else
    echo "Network mep-services-network already exists."
fi

# Build Docker images (if not skipped)
if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo -e "${PURPLE}🔨 Building Docker Images${NC}"
    echo -e "${PURPLE}========================${NC}"
    
    # Build infrastructure services
    echo -e "${CYAN}📦 Building infrastructure services...${NC}"
    cd services
    docker compose build --no-cache
    cd ..
    
    # Build core services
    echo -e "${CYAN}📦 Building core services...${NC}"
    cd core
    docker compose build --no-cache
    cd ..
    
    echo -e "${GREEN}✅ All Docker images built successfully${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping Docker build (--skip-build flag used)${NC}"
fi

# Check and build file-watcher image specifically (always build if missing)
echo -e "${CYAN}📦 Checking file-watcher image...${NC}"
if ! docker images | grep -q "mep-file-watcher"; then
    echo -e "${YELLOW}⚠️  File-watcher image not found. Building...${NC}"
    cd core
    docker compose build file-watcher
    cd ..
    echo -e "${GREEN}✅ File-watcher image built successfully${NC}"
else
    echo -e "${GREEN}✅ File-watcher image already exists${NC}"
fi



# Start services (if not skipped)
if [ "$SKIP_SERVICES" = false ]; then
    echo ""
    echo -e "${PURPLE}🚀 Starting Services${NC}"
    echo -e "${PURPLE}==================${NC}"
    
    # Step 1: Start infrastructure services first
    echo -e "${CYAN}🔧 Starting infrastructure services...${NC}"
    cd services
    docker compose up -d postgres elasticsearch kibana qdrant neo4j redis minio n8n flowise
    
    echo -e "${CYAN}🔧 Starting development admin UIs...${NC}"
    docker compose --profile dev up -d pgadmin redis-commander
    
    echo -e "${CYAN}🔧 Starting monitoring services...${NC}"
    docker compose --profile monitoring up -d prometheus grafana
    
    echo -e "${BLUE}⏳ Waiting for infrastructure services to be ready...${NC}"
    sleep 45
    
    # Check infrastructure services health
    echo -e "${BLUE}🔍 Checking infrastructure services health...${NC}"
    
    # PostgreSQL health check
    if docker compose exec -T postgres pg_isready -U mep_user -d mep_ainabox > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL is starting...${NC}"
    fi
    
    # Elasticsearch health check
    if curl -f -u elastic:elastic_password http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Elasticsearch is ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Elasticsearch is starting...${NC}"
    fi
    
    # Qdrant health check
    if curl -f http://localhost:6333/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Qdrant is ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Qdrant is starting...${NC}"
    fi
    
    # Neo4j health check
    if curl -f http://localhost:7474/browser/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Neo4j is ready${NC}"
    else
        echo -e "${YELLOW}⚠️  Neo4j is starting...${NC}"
    fi
    
    cd ..
    
    # Step 2: Start native core processing services
    echo -e "${CYAN}🔧 Starting native core processing services...${NC}"
    cd core
    
    # Install Python requirements if not already done
    echo -e "${BLUE}🐍 Installing Python requirements for native core services...${NC}"
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements_native.txt --user
        echo -e "${GREEN}✅ Python requirements installed${NC}"
    else
        echo -e "${RED}❌ pip3 not found. Please install Python 3 and pip3 first.${NC}"
        exit 1
    fi
    
    # Initialize database
    echo -e "${BLUE}🗄️  Initializing database...${NC}"
    cd core_processor
    if [ -f "init_database.sh" ]; then
        chmod +x init_database.sh
        ./init_database.sh
        echo -e "${GREEN}✅ Database initialized${NC}"
    else
        echo -e "${YELLOW}⚠️  init_database.sh not found. Database may not be properly initialized.${NC}"
    fi
    cd ..
    
    # Start native services
    echo -e "${BLUE}🚀 Starting native core processing services...${NC}"
    ./start_native_services.sh
    
    echo -e "${BLUE}⏳ Waiting for native core services to be ready...${NC}"
    sleep 30
    
    # Check native core services health
    echo -e "${BLUE}🔍 Checking native core services health...${NC}"
    
    # Define service ports for native processing
    declare -A service_ports=(
        ["api-gateway"]=8011
        ["core-processor"]=8001
        ["document-router"]=8002
        ["processing-pipeline"]=8003
        ["storage-manager"]=8004
        ["text-processor"]=8005
        ["metadata-processor"]=8006
        ["embedding-processor"]=8007
        ["entity-processor"]=8008
        ["file-watcher"]=8009
    )
    
    for service in "${!service_ports[@]}"; do
        port="${service_ports[$service]}"
        if curl -f http://localhost:$port/health > /dev/null 2>&1 || curl -f http://localhost:$port/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is healthy (port $port)${NC}"
        else
            echo -e "${YELLOW}⚠️  $service health check failed (port $port)${NC}"
        fi
    done
    
    cd ..
    
    echo -e "${GREEN}✅ All services started successfully${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping service startup (--skip-services flag used)${NC}"
fi

# Start dashboard (admin interface)
echo ""
echo -e "${PURPLE}🎛️  Starting Dashboard (Admin Interface)${NC}"
echo -e "${PURPLE}==========================================${NC}"

# Clean up existing dashboard processes
echo -e "${BLUE}🧹 Cleaning up existing dashboard processes...${NC}"
if pgrep -f "python3.*dashboard.*main.py" > /dev/null; then
    echo "Stopping existing dashboard process..."
    pkill -f "python3.*dashboard.*main.py" || true
    sleep 2
fi

# Clean up stale PID files
if [ -f "core/dashboard.pid" ]; then
    PID=$(cat core/dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale dashboard PID file..."
        rm -f core/dashboard.pid
    fi
fi

# Start host volume manager service (DISABLED - user preference)
# echo -e "${CYAN}🚀 Starting host volume manager service...${NC}"
# cd core
# ./start_host_volume_manager.sh

# Start dashboard on host
echo -e "${CYAN}🚀 Starting dashboard on host...${NC}"
./start_dashboard_host.sh --background

# Wait for dashboard to be ready
echo -e "${BLUE}⏳ Waiting for dashboard to start...${NC}"
sleep 15

# Check if dashboard is healthy
echo -e "${BLUE}🔍 Checking dashboard health...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Dashboard is ready!${NC}"
        break
    else
        echo -e "${YELLOW}⏳ Waiting for dashboard... (attempt $((attempt + 1))/$max_attempts)${NC}"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Dashboard failed to start properly.${NC}"
    echo "Check logs with: tail -f core/logs/dashboard.log"
    exit 1
fi

cd ..

# Start Qdrant UI if available
echo -e "${CYAN}🔍 Starting Qdrant UI...${NC}"
cd services
if [ -d "qdrant-ui" ]; then
    ./scripts/start-qdrant-ui-daemon.sh
    
    # Wait for Qdrant UI to be ready
    echo -e "${BLUE}⏳ Waiting for Qdrant UI to start...${NC}"
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:7070/index.html > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Qdrant UI is ready!${NC}"
            break
        else
            echo -e "${YELLOW}⏳ Waiting for Qdrant UI... (attempt $((attempt + 1))/$max_attempts)${NC}"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ Qdrant UI failed to start properly.${NC}"
        echo "Check logs with: tail -f services/qdrant-ui.log"
        # Don't exit, just warn
    else
        echo -e "${GREEN}✅ Qdrant UI started successfully${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Qdrant UI directory not found${NC}"
fi
cd ..

echo ""
echo -e "${GREEN}🎉 MEP AI NABOX System Initialization Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}🌐 Service URLs:${NC}"
echo -e "${GREEN}  Dashboard:${NC} http://localhost:8010"
echo -e "${GREEN}  Admin Panel:${NC} http://localhost:8010/admin"
echo -e "${GREEN}  API Gateway:${NC} http://localhost:8011"
echo -e "${GREEN}  Core Processor:${NC} http://localhost:8001"
echo -e "${GREEN}  Document Router:${NC} http://localhost:8002"
echo -e "${GREEN}  Processing Pipeline:${NC} http://localhost:8003"
echo -e "${GREEN}  Storage Manager:${NC} http://localhost:8004"
echo -e "${GREEN}  Text Processor:${NC} http://localhost:8005"
echo -e "${GREEN}  Metadata Processor:${NC} http://localhost:8006"
echo -e "${GREEN}  Embedding Processor:${NC} http://localhost:8007"
echo -e "${GREEN}  Entity Processor:${NC} http://localhost:8008"
echo -e "${GREEN}  File Watcher:${NC} http://localhost:8009"
echo ""
echo -e "${BLUE}🔧 Infrastructure Services:${NC}"
echo -e "${GREEN}  PostgreSQL:${NC} localhost:5432"
echo -e "${GREEN}  Elasticsearch:${NC} http://localhost:9200"
echo -e "${GREEN}  Kibana:${NC} http://localhost:5601"
echo -e "${GREEN}  Qdrant:${NC} http://localhost:6333"
echo -e "${GREEN}  Neo4j Browser:${NC} http://localhost:7474"
echo -e "${GREEN}  Redis:${NC} localhost:6379"
echo -e "${GREEN}  MinIO Console:${NC} http://localhost:9001"
echo -e "${GREEN}  n8n:${NC} http://localhost:5678"
echo -e "${GREEN}  Flowise:${NC} http://localhost:3001"
echo ""
echo -e "${BLUE}📊 Useful Commands:${NC}"
echo -e "${CYAN}  View all containers:${NC} docker ps"
echo -e "${CYAN}  View logs:${NC} docker compose logs -f"
echo -e "${CYAN}  Stop all services:${NC} ./stop_system.sh"
echo -e "${CYAN}  Restart dashboard:${NC} cd core && ./restart_dashboard.sh"
echo -e "${CYAN}  Health check:${NC} ./health_check.sh"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "1. Open http://localhost:8010 in your browser"
echo "2. Go to the Admin panel to monitor services"
echo "3. Upload documents to start processing"
echo ""
echo -e "${GREEN}✅ System is ready for use!${NC}" 