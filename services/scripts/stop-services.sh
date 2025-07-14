#!/bin/bash

# MEP AI NABOX Services - Stop Script
# This script stops all running services using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🛑 Stopping MEP AI NABOX Services...${NC}"

# Change to services directory
cd "$SERVICES_DIR"

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not available.${NC}"
    exit 1
fi

# Check if services are running
if ! docker compose ps > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  No services are currently running.${NC}"
    exit 0
fi

# Show current service status
echo -e "${BLUE}📊 Current Service Status:${NC}"
docker compose ps

# Stop all services
echo -e "${BLUE}🔧 Stopping all services...${NC}"
docker compose down

# Check if user wants to remove volumes (data)
if [ "$1" = "--remove-volumes" ] || [ "$1" = "-v" ]; then
    echo -e "${YELLOW}⚠️  Removing all data volumes...${NC}"
    echo -e "${YELLOW}⚠️  This will permanently delete all data!${NC}"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose down -v
        echo -e "${GREEN}✅ All services stopped and volumes removed.${NC}"
    else
        echo -e "${YELLOW}⚠️  Volumes preserved. Services stopped.${NC}"
    fi
else
    echo -e "${GREEN}✅ All services stopped. Data volumes preserved.${NC}"
fi

# Show final status
echo -e "${BLUE}📊 Final Service Status:${NC}"
docker compose ps

echo -e "${GREEN}✅ Services stopped successfully!${NC}"
echo -e "${YELLOW}💡 Use './scripts/start-services.sh' to start services again.${NC}" 