#!/bin/bash

# MEP AI NABOX - Dashboard Docker Stop Script
# This script stops the dashboard service running in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 MEP AI NABOX - Dashboard Docker Stop${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found. Please run this script from the core directory.${NC}"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Error: docker compose is not available${NC}"
    exit 1
fi

# Stop dashboard container
echo -e "${BLUE}🛑 Stopping dashboard container...${NC}"
if docker ps -q -f name=mep-dashboard | grep -q .; then
    echo "Stopping mep-dashboard container..."
    docker stop mep-dashboard
    docker rm mep-dashboard
    echo -e "${GREEN}✅ Dashboard container stopped and removed${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard container not found${NC}"
fi

# Also stop any dashboard processes running on host
echo -e "${BLUE}🛑 Stopping dashboard processes on host...${NC}"
if pgrep -f "python3.*dashboard.*main.py" > /dev/null; then
    echo "Stopping dashboard process on host..."
    pkill -f "python3.*dashboard.*main.py" || true
    sleep 2
    echo -e "${GREEN}✅ Dashboard process on host stopped${NC}"
else
    echo -e "${YELLOW}⚠️  No dashboard process found on host${NC}"
fi

# Clean up stale PID files
if [ -f "dashboard.pid" ]; then
    PID=$(cat dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale dashboard PID file..."
        rm -f dashboard.pid
        echo -e "${GREEN}✅ Stale PID file removed${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 Dashboard stopped successfully!${NC}"
echo -e "${GREEN}===============================${NC}"
echo ""
echo -e "${BLUE}📊 To restart the dashboard:${NC}"
echo -e "${CYAN}  ./start_dashboard_docker.sh --background${NC}"
echo ""
