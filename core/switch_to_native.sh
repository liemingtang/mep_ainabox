#!/bin/bash

# MEP AI NABOX - Switch to Native Services
# This script stops Docker services and starts native services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Switching from Docker to Native Services${NC}"
echo "=============================================="

# Stop Docker services
echo -e "${YELLOW}🛑 Stopping Docker services...${NC}"
cd /home/lie/repo_mep/mep_ainabox/core

# Stop core processing services
docker stop mep-api-gateway mep-core-processor mep-document-router mep-processing-pipeline mep-storage-manager mep-text-processor mep-metadata-processor mep-embedding-processor mep-entity-processor mep-queue-worker mep-status-worker mep-file-watcher 2>/dev/null || true

echo -e "${GREEN}✅ Docker services stopped${NC}"

# Start native services
echo -e "${BLUE}🚀 Starting native services...${NC}"
./start_native_services.sh

echo -e "${GREEN}✅ Native services started${NC}"
echo -e "${CYAN}📊 Use './start_native_services.sh --status' to check service status${NC}"
echo -e "${CYAN}📋 Use './start_native_services.sh --logs [service]' to view logs${NC}" 