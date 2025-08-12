#!/bin/bash

# HuggingFace Embeddings Health Check Script
# This script checks the health of the HuggingFace embeddings service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧠 HuggingFace Embeddings Health Check${NC}"
echo "=========================================="

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$(dirname "$SCRIPT_DIR")"

# Change to services directory
cd "$SERVICES_DIR"

# Check if Docker Compose is running
if ! docker compose ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker Compose is not running in this directory.${NC}"
    exit 1
fi

# Function to check service health
check_service() {
    local service_name=$1
    local check_command=$2
    local description=$3
    
    echo -n "Checking $description... "
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}❌ UNHEALTHY${NC}"
        return 1
    fi
}

# Function to check service status
check_service_status() {
    local service_name=$1
    local status=$(docker compose ps -q "$service_name" 2>/dev/null | wc -l)
    
    if [ "$status" -eq 1 ]; then
        echo -e "${GREEN}✅ RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ NOT RUNNING${NC}"
        return 1
    fi
}

echo -e "\n${BLUE}📊 Service Status Check${NC}"
echo "------------------------"

# Check HuggingFace Embeddings Status
echo -n "HuggingFace Embeddings Status: "
if check_service_status "huggingface-embeddings"; then
    echo -e "\n${BLUE}🔍 Health Check${NC}"
    echo "------------------------"
    
    # Check if the service is responding to HTTP requests
    if check_service "huggingface-embeddings" "curl -f http://localhost:8082/" "HTTP Endpoint"; then
        echo -e "\n${GREEN}✅ HuggingFace Embeddings is healthy and responding${NC}"
    else
        echo -e "\n${RED}❌ HuggingFace Embeddings is not responding to HTTP requests${NC}"
    fi
    
    # Check container logs for any errors
    echo -e "\n${BLUE}📋 Recent Logs (last 10 lines)${NC}"
    echo "--------------------------------"
    docker compose logs --tail=10 huggingface-embeddings
    
    # Show container details
    echo -e "\n${BLUE}📋 Container Details${NC}"
    echo "---------------------"
    docker compose ps huggingface-embeddings
    
    # Show resource usage
    echo -e "\n${BLUE}📊 Resource Usage${NC}"
    echo "------------------"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" mep-huggingface-embeddings
    
else
    echo -e "\n${RED}❌ HuggingFace Embeddings service is not running${NC}"
    echo -e "${YELLOW}💡 To start the service, run:${NC}"
    echo -e "   docker compose up -d huggingface-embeddings"
fi

echo -e "\n${BLUE}🌐 Service Information${NC}"
echo "------------------------"
echo -e "${CYAN}Service URL:${NC} http://localhost:8082"
echo -e "${CYAN}Container Name:${NC} mep-huggingface-embeddings"
echo -e "${CYAN}Model:${NC} sentence-transformers/all-MiniLM-L6-v2"
echo -e "${CYAN}Port Mapping:${NC} 8082:80"

echo -e "\n${BLUE}🔧 Useful Commands${NC}"
echo "-------------------"
echo -e "${CYAN}View logs:${NC} docker compose logs -f huggingface-embeddings"
echo -e "${CYAN}Restart service:${NC} docker compose restart huggingface-embeddings"
echo -e "${CYAN}Stop service:${NC} docker compose stop huggingface-embeddings"
echo -e "${CYAN}Start service:${NC} docker compose up -d huggingface-embeddings"

echo -e "\n${GREEN}✅ Health check complete!${NC}"
