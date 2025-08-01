#!/bin/bash

# MEP AI NABOX - Health Check Script
# This script checks the health of all services

set -e

# Load environment variables
if [ -f "services/.env" ]; then
    echo "Loading environment variables from services/.env..."
    set -a
    source services/.env
    set +a
elif [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -a
    source .env
    set +a
else
    echo "⚠️  No .env file found. Using default values."
fi

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
    echo "MEP AI NABOX - Health Check Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script checks the health of all MEP AI NABOX services."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help              Show this help message"
    echo "  --quick                 Quick check (skip detailed health endpoints)"
    echo "  --containers-only       Check only Docker containers"
    echo "  --services-only         Check only service health endpoints"
    echo ""
    echo "WHAT IT CHECKS:"
    echo "  • Infrastructure Services: PostgreSQL, Elasticsearch, Kibana, Qdrant, Neo4j, Redis, MinIO, n8n, Flowise"
    echo "  • Core Services: API Gateway, Core Processor, Document Router, Processing Pipeline, Storage Manager, File Watcher"
    echo "  • UI Services: Dashboard, Qdrant UI"
    echo "  • Health Endpoints: All service health checks"
    echo "  • System Summary: Container count, process count"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                      # Full health check"
    echo "  $0 --quick              # Quick check (faster)"
    echo "  $0 --containers-only    # Check only Docker containers"
    echo "  $0 --services-only      # Check only service health endpoints"
    echo ""
    echo "SERVICE URLs:"
    echo "  Dashboard: http://localhost:8010"
    echo "  Admin Panel: http://localhost:8010/admin"
    echo "  API Gateway: http://localhost:8000"
    echo "  Core Processor: http://localhost:8001"
    echo ""
    echo "For more information, see INITIALIZATION_GUIDE.md"
}

# Parse command line arguments
QUICK_CHECK=false
CONTAINERS_ONLY=false
SERVICES_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --quick)
            QUICK_CHECK=true
            shift
            ;;
        --containers-only)
            CONTAINERS_ONLY=true
            shift
            ;;
        --services-only)
            SERVICES_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MEP AI NABOX - Health Check${NC}"
echo -e "${BLUE}==============================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "core/docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: core/docker-compose.yml not found. Please run this script from the mep_ainabox root directory.${NC}"
    exit 1
fi

# Determine what to check based on options
if [ "$CONTAINERS_ONLY" = true ]; then
    echo -e "${YELLOW}📋 Running containers-only check...${NC}"
elif [ "$SERVICES_ONLY" = true ]; then
    echo -e "${YELLOW}📋 Running services-only check...${NC}"
elif [ "$QUICK_CHECK" = true ]; then
    echo -e "${YELLOW}📋 Running quick check...${NC}"
else
    echo -e "${YELLOW}📋 Running full health check...${NC}"
fi
echo ""

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local port=$3
    
    if curl -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is healthy${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not responding${NC}"
        return 1
    fi
}

# Function to check Docker container
check_container() {
    local container_name=$1
    local service_name=$2
    
    if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        local status=$(docker ps --format "{{.Status}}" --filter "name=^${container_name}$")
        echo -e "${GREEN}✅ $service_name is running ($status)${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not running${NC}"
        return 1
    fi
}

# Function to check process
check_process() {
    local process_pattern=$1
    local service_name=$2
    
    if pgrep -f "$process_pattern" > /dev/null; then
        echo -e "${GREEN}✅ $service_name is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name is not running${NC}"
        return 1
    fi
}

# Check containers (if not services-only)
if [ "$SERVICES_ONLY" = false ]; then
    echo -e "${PURPLE}🔧 Infrastructure Services${NC}"
    echo -e "${PURPLE}=======================${NC}"

    # Check infrastructure containers
    check_container "mep-postgres" "PostgreSQL"
    check_container "mep-elasticsearch" "Elasticsearch"
    check_container "mep-kibana" "Kibana"
    check_container "mep-qdrant" "Qdrant"
    check_container "mep-neo4j" "Neo4j"
    check_container "mep-redis" "Redis"
    check_container "mep-minio" "MinIO"
    check_container "mep-n8n" "n8n"
    check_container "mep-flowise" "Flowise"

    echo ""
    echo -e "${PURPLE}🔧 Core Services${NC}"
    echo -e "${PURPLE}===============${NC}"

    # Check core containers
    check_container "mep-api-gateway" "API Gateway"
    check_container "mep-core-processor" "Core Processor"
    check_container "mep-document-router" "Document Router"
    check_container "mep-processing-pipeline" "Processing Pipeline"
    check_container "mep-storage-manager" "Storage Manager"
    check_container "mep-file-watcher" "File Watcher"

    echo ""
    echo -e "${PURPLE}🎛️  UI Services${NC}"
    echo -e "${PURPLE}==============${NC}"

    # Check dashboard process
    check_process "python3.*main.py" "Dashboard"

    # Check Qdrant UI process
    check_process "python3.*server.py" "Qdrant UI"
fi

echo ""
# Check service health endpoints (if not containers-only)
if [ "$CONTAINERS_ONLY" = false ]; then
    echo -e "${PURPLE}🌐 Service Health Checks${NC}"
    echo -e "${PURPLE}======================${NC}"

    # Check service health endpoints
    check_service "Dashboard" "http://localhost:8010/api/health" "8010"
    check_service "API Gateway" "http://localhost:8000/health" "8000"
    check_service "Core Processor" "http://localhost:8001/health" "8001"
    check_service "Document Router" "http://localhost:8002/health" "8002"
    check_service "Processing Pipeline" "http://localhost:8003/health" "8003"
    check_service "Storage Manager" "http://localhost:8004/health" "8004"

    # Skip detailed infrastructure checks for quick mode
    if [ "$QUICK_CHECK" = false ]; then
        echo ""
        echo -e "${PURPLE}🔧 Infrastructure Health Checks${NC}"
        echo -e "${PURPLE}=============================${NC}"

        # Check infrastructure services
        if curl -f -u elastic:elastic_password http://localhost:9200/_cluster/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Elasticsearch is healthy${NC}"
        else
            echo -e "${RED}❌ Elasticsearch is not responding${NC}"
        fi

        if curl -f http://localhost:5601/api/status > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Kibana is healthy${NC}"
        else
            echo -e "${RED}❌ Kibana is not responding${NC}"
        fi

        if curl -f -H "api-key: ${QDRANT_API_KEY:-qdrant_api_key}" http://localhost:6333/collections > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Qdrant is healthy${NC}"
        else
            echo -e "${RED}❌ Qdrant is not responding${NC}"
        fi

        if curl -f http://localhost:7474/browser/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Neo4j Browser is healthy${NC}"
        else
            echo -e "${RED}❌ Neo4j Browser is not responding${NC}"
        fi

        if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
            echo -e "${GREEN}✅ MinIO is healthy${NC}"
        else
            echo -e "${RED}❌ MinIO is not responding${NC}"
        fi

        if curl -f http://localhost:5678/healthz > /dev/null 2>&1; then
            echo -e "${GREEN}✅ n8n is healthy${NC}"
        else
            echo -e "${RED}❌ n8n is not responding${NC}"
        fi

        if curl -f http://localhost:3001/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Flowise is healthy${NC}"
        else
            echo -e "${RED}❌ Flowise is not responding${NC}"
        fi

        # Check admin UIs
        if curl -f http://localhost:8080/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ pgAdmin is healthy${NC}"
        else
            echo -e "${RED}❌ pgAdmin is not responding${NC}"
        fi

        if curl -f http://localhost:8081/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis Commander is healthy${NC}"
        else
            echo -e "${RED}❌ Redis Commander is not responding${NC}"
        fi

        if curl -f http://localhost:9090/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Prometheus is healthy${NC}"
        else
            echo -e "${RED}❌ Prometheus is not responding${NC}"
        fi

        if curl -f http://localhost:3002/ > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Grafana is healthy${NC}"
        else
            echo -e "${RED}❌ Grafana is not responding${NC}"
        fi
    fi
fi

echo ""
echo -e "${PURPLE}📊 System Summary${NC}"
echo -e "${PURPLE}================${NC}"

# Count running containers
total_containers=$(docker ps --filter "name=mep-" --format "{{.Names}}" | wc -l)
echo -e "${CYAN}Total MEP containers running: $total_containers${NC}"

# Count running processes
dashboard_running=$(pgrep -f "python3.*main.py" | wc -l)
qdrant_ui_running=$(pgrep -f "python3.*server.py" | wc -l)
echo -e "${CYAN}Dashboard processes: $dashboard_running${NC}"
echo -e "${CYAN}Qdrant UI processes: $qdrant_ui_running${NC}"

echo ""
echo -e "${BLUE}🌐 Service URLs${NC}"
echo -e "${GREEN}  Dashboard:${NC} http://localhost:8010"
echo -e "${GREEN}  Admin Panel:${NC} http://localhost:8010/admin"
echo -e "${GREEN}  API Gateway:${NC} http://localhost:8000"
echo -e "${GREEN}  Core Processor:${NC} http://localhost:8001"
echo -e "${GREEN}  Document Router:${NC} http://localhost:8002"
echo -e "${GREEN}  Processing Pipeline:${NC} http://localhost:8003"
echo -e "${GREEN}  Storage Manager:${NC} http://localhost:8004"
echo -e "${GREEN}  Elasticsearch:${NC} http://localhost:9200"
echo -e "${GREEN}  Kibana:${NC} http://localhost:5601"
echo -e "${GREEN}  Qdrant:${NC} http://localhost:6333"
echo -e "${GREEN}  Neo4j Browser:${NC} http://localhost:7474"
echo -e "${GREEN}  MinIO Console:${NC} http://localhost:9001"
echo -e "${GREEN}  n8n:${NC} http://localhost:5678"
echo -e "${GREEN}  Flowise:${NC} http://localhost:3001"
echo -e "${GREEN}  pgAdmin:${NC} http://localhost:8080"
echo -e "${GREEN}  Redis Commander:${NC} http://localhost:8081"
echo -e "${GREEN}  Prometheus:${NC} http://localhost:9090"
echo -e "${GREEN}  Grafana:${NC} http://localhost:3002"

echo ""
echo -e "${GREEN}✅ Health check complete!${NC}" 