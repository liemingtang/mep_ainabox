#!/bin/bash

# MEP AI NABOX Services - Start Script
# This script starts all required services using Docker Compose

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

echo -e "${BLUE}🚀 Starting MEP AI NABOX Services...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not available. Please install Docker Compose first.${NC}"
    exit 1
fi

# Change to services directory
cd "$SERVICES_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Created .env file from template.${NC}"
        echo -e "${YELLOW}⚠️  Please review and update the .env file with your configuration.${NC}"
    else
        echo -e "${RED}❌ env.example file not found. Please create a .env file manually.${NC}"
        exit 1
    fi
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p volumes/{postgres,elasticsearch,kibana,qdrant,neo4j,redis,minio,n8n,flowise,pgadmin,prometheus,grafana}
mkdir -p config/{postgres,elasticsearch,kibana,qdrant,neo4j,redis,minio}
mkdir -p monitoring/{prometheus,grafana,logs}

# Set proper permissions for volumes
echo -e "${BLUE}🔐 Setting proper permissions...${NC}"
sudo chown -R 1000:1000 volumes/elasticsearch 2>/dev/null || true
sudo chown -R 1000:1000 volumes/neo4j 2>/dev/null || true
sudo chown -R 1000:1000 volumes/redis 2>/dev/null || true
sudo chown -R 1000:1000 volumes/minio 2>/dev/null || true

# Start core services first
echo -e "${BLUE}🔧 Starting core services...${NC}"
docker compose up -d postgres elasticsearch kibana qdrant neo4j redis minio n8n flowise

# Wait for core services to be ready
echo -e "${BLUE}⏳ Waiting for core services to be ready...${NC}"
sleep 30

# Check core services health
echo -e "${BLUE}🔍 Checking core services health...${NC}"

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

# Kibana health check
if curl -f http://localhost:5601/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kibana is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Kibana is starting...${NC}"
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

# Redis health check
if docker compose exec -T redis redis-cli --raw incr ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Redis is starting...${NC}"
fi

# MinIO health check
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MinIO is ready${NC}"
else
    echo -e "${YELLOW}⚠️  MinIO is starting...${NC}"
fi

# n8n health check
if curl -f http://localhost:5678/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✅ n8n is ready${NC}"
else
    echo -e "${YELLOW}⚠️  n8n is starting...${NC}"
fi

# Flowise health check
if curl -f http://localhost:3001/api/v1/chatflows > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Flowise is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Flowise is starting...${NC}"
fi

# Start development services if requested
if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    echo -e "${BLUE}🔧 Starting development services...${NC}"
    docker compose --profile dev up -d
fi

# Start monitoring services if requested
if [ "$1" = "--monitoring" ] || [ "$1" = "-m" ]; then
    echo -e "${BLUE}🔧 Starting monitoring services...${NC}"
    docker compose --profile monitoring up -d
fi

# Show service status
echo -e "${BLUE}📊 Service Status:${NC}"
docker compose ps

# Show service URLs
echo -e "${BLUE}🌐 Service URLs:${NC}"
echo -e "${GREEN}PostgreSQL:${NC} localhost:5432"
echo -e "${GREEN}Elasticsearch:${NC} http://localhost:9200"
echo -e "${GREEN}Kibana:${NC} http://localhost:5601"
echo -e "${GREEN}Qdrant:${NC} http://localhost:6333"
echo -e "${GREEN}Neo4j Browser:${NC} http://localhost:7474"
echo -e "${GREEN}Redis:${NC} localhost:6379"
echo -e "${GREEN}MinIO Console:${NC} http://localhost:9001"
echo -e "${GREEN}n8n:${NC} http://localhost:5678"
echo -e "${GREEN}Flowise:${NC} http://localhost:3001"

if [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
    echo -e "${GREEN}pgAdmin:${NC} http://localhost:8080"
    echo -e "${GREEN}Elasticsearch Head:${NC} http://localhost:9100"
    echo -e "${GREEN}Redis Commander:${NC} http://localhost:8081"
fi

if [ "$1" = "--monitoring" ] || [ "$1" = "-m" ]; then
    echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
    echo -e "${GREEN}Grafana:${NC} http://localhost:3000"
fi

echo -e "${GREEN}✅ All services started successfully!${NC}"
echo -e "${YELLOW}💡 Use './scripts/health-check.sh' to verify all services are healthy.${NC}"
echo -e "${YELLOW}💡 Use './scripts/stop-services.sh' to stop all services.${NC}" 