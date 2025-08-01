#!/bin/bash

# MEP AI NABOX - System Stop Script
# This script stops all services and cleans up processes

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
    echo "MEP AI NABOX - System Stop Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script gracefully stops all services and cleans up processes."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help              Show this help message"
    echo "  --force                 Force stop (kill processes immediately)"
    echo ""
    echo "WHAT IT STOPS:"
    echo "  • Dashboard processes (python3 main.py)"
    echo "  • Qdrant UI processes (python3 server.py)"
    echo "  • All Docker containers (mep-*)"
    echo "  • Docker network (mep-services-network)"
    echo "  • PID files cleanup"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                      # Graceful shutdown"
    echo "  $0 --force              # Force stop all processes"
    echo ""
    echo "To restart the system:"
    echo "  ./init_system.sh"
    echo ""
    echo "For more information, see INITIALIZATION_GUIDE.md"
}

# Parse command line arguments
FORCE_STOP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --force)
            FORCE_STOP=true
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

echo -e "${BLUE}🛑 MEP AI NABOX - System Shutdown${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "core/docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: core/docker-compose.yml not found. Please run this script from the mep_ainabox root directory.${NC}"
    exit 1
fi

# Stop dashboard processes
echo -e "${BLUE}🧹 Stopping dashboard processes...${NC}"
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "Stopping dashboard process..."
    if [ "$FORCE_STOP" = true ]; then
        pkill -9 -f "python3.*main.py" || true
    else
        pkill -f "python3.*main.py" || true
    fi
    sleep 2
fi

# Stop Qdrant UI processes
echo -e "${BLUE}🧹 Stopping Qdrant UI processes...${NC}"
if pgrep -f "python3.*server.py" > /dev/null; then
    echo "Stopping Qdrant UI process..."
    if [ "$FORCE_STOP" = true ]; then
        pkill -9 -f "python3.*server.py" || true
    else
        pkill -f "python3.*server.py" || true
    fi
    sleep 2
fi

# Clean up PID files
echo -e "${BLUE}🧹 Cleaning up PID files...${NC}"
if [ -f "core/dashboard.pid" ]; then
    PID=$(cat core/dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale dashboard PID file..."
        rm -f core/dashboard.pid
    fi
fi

if [ -f "services/qdrant-ui.pid" ]; then
    PID=$(cat services/qdrant-ui.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale Qdrant UI PID file..."
        rm -f services/qdrant-ui.pid
    fi
fi

# Stop core services
echo -e "${BLUE}🛑 Stopping core services...${NC}"
cd core
docker compose down
cd ..

# Stop infrastructure services
echo -e "${BLUE}🛑 Stopping infrastructure services...${NC}"
cd services
docker compose down
cd ..

# Stop any remaining containers with mep- prefix
echo -e "${BLUE}🧹 Cleaning up any remaining MEP containers...${NC}"
if [ "$FORCE_STOP" = true ]; then
    docker ps --filter "name=mep-" --format "{{.Names}}" | xargs -r docker kill
else
    docker ps --filter "name=mep-" --format "{{.Names}}" | xargs -r docker stop
fi
docker ps -a --filter "name=mep-" --format "{{.Names}}" | xargs -r docker rm

# Remove Docker network if no containers are using it
echo -e "${BLUE}🌐 Cleaning up Docker network...${NC}"
if docker network ls | grep -q "mep-services-network"; then
    if ! docker network inspect mep-services-network | grep -q "Containers"; then
        echo "Removing mep-services-network..."
        docker network rm mep-services-network
    else
        echo "Network mep-services-network is still in use, keeping it."
    fi
fi

echo ""
echo -e "${GREEN}✅ System shutdown complete!${NC}"
echo ""
echo -e "${YELLOW}💡 To restart the system:${NC}"
echo "  ./init_system.sh"
echo ""
echo -e "${YELLOW}💡 To start only the dashboard:${NC}"
echo "  ./start_admin.sh" 