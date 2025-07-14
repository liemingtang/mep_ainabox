#!/bin/bash

# MEP AI NABOX Services - Health Check Script
# This script checks the health of all running services

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

echo -e "${BLUE}🔍 MEP AI NABOX Services Health Check${NC}"
echo "=================================================="

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

# Initialize counters
healthy_count=0
total_count=0

echo -e "\n${BLUE}📊 Service Status Check${NC}"
echo "------------------------"

# Check PostgreSQL
echo -n "PostgreSQL Status: "
if check_service_status "postgres"; then
    ((healthy_count++))
fi
((total_count++))

# Check Elasticsearch
echo -n "Elasticsearch Status: "
if check_service_status "elasticsearch"; then
    ((healthy_count++))
fi
((total_count++))

# Check Qdrant
echo -n "Qdrant Status: "
if check_service_status "qdrant"; then
    ((healthy_count++))
fi
((total_count++))

# Check Neo4j
echo -n "Neo4j Status: "
if check_service_status "neo4j"; then
    ((healthy_count++))
fi
((total_count++))

# Check Redis
echo -n "Redis Status: "
if check_service_status "redis"; then
    ((healthy_count++))
fi
((total_count++))

# Check MinIO
echo -n "MinIO Status: "
if check_service_status "minio"; then
    ((healthy_count++))
fi
((total_count++))

echo -e "\n${BLUE}🔍 Service Health Check${NC}"
echo "------------------------"

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# PostgreSQL Health Check
if check_service "postgres" "docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-mep_user} -d ${POSTGRES_DB:-mep_ainabox}" "PostgreSQL"; then
    ((healthy_count++))
fi
((total_count++))

# Elasticsearch Health Check
if check_service "elasticsearch" "curl -f -u ${ELASTICSEARCH_USERNAME:-elastic}:${ELASTICSEARCH_PASSWORD:-elastic_password} http://localhost:9200/_cluster/health" "Elasticsearch"; then
    ((healthy_count++))
fi
((total_count++))

# Qdrant Health Check
if check_service "qdrant" "curl -f http://localhost:6333/health" "Qdrant"; then
    ((healthy_count++))
fi
((total_count++))

# Neo4j Health Check
if check_service "neo4j" "curl -f http://localhost:7474/browser/" "Neo4j"; then
    ((healthy_count++))
fi
((total_count++))

# Redis Health Check
if check_service "redis" "docker compose exec -T redis redis-cli --raw incr ping" "Redis"; then
    ((healthy_count++))
fi
((total_count++))

# MinIO Health Check
if check_service "minio" "curl -f http://localhost:9000/minio/health/live" "MinIO"; then
    ((healthy_count++))
fi
((total_count++))

# Check development services if they exist
echo -e "\n${BLUE}🔧 Development Services Check${NC}"
echo "--------------------------------"

# pgAdmin
if docker compose ps pgadmin > /dev/null 2>&1; then
    echo -n "pgAdmin Status: "
    if check_service_status "pgadmin"; then
        ((healthy_count++))
    fi
    ((total_count++))
    
    if check_service "pgadmin" "curl -f http://localhost:8080" "pgAdmin"; then
        ((healthy_count++))
    fi
    ((healthy_count++))
    fi
    ((total_count++))
fi

# Elasticsearch Head
if docker compose ps elasticsearch-head > /dev/null 2>&1; then
    echo -n "Elasticsearch Head Status: "
    if check_service_status "elasticsearch-head"; then
        ((healthy_count++))
    fi
    ((total_count++))
    
    if check_service "elasticsearch-head" "curl -f http://localhost:9100" "Elasticsearch Head"; then
        ((healthy_count++))
    fi
    ((total_count++))
fi

# Redis Commander
if docker compose ps redis-commander > /dev/null 2>&1; then
    echo -n "Redis Commander Status: "
    if check_service_status "redis-commander"; then
        ((healthy_count++))
    fi
    ((total_count++))
    
    if check_service "redis-commander" "curl -f http://localhost:8081" "Redis Commander"; then
        ((healthy_count++))
    fi
    ((total_count++))
fi

# Check monitoring services if they exist
echo -e "\n${BLUE}📊 Monitoring Services Check${NC}"
echo "--------------------------------"

# Prometheus
if docker compose ps prometheus > /dev/null 2>&1; then
    echo -n "Prometheus Status: "
    if check_service_status "prometheus"; then
        ((healthy_count++))
    fi
    ((total_count++))
    
    if check_service "prometheus" "curl -f http://localhost:9090/-/healthy" "Prometheus"; then
        ((healthy_count++))
    fi
    ((total_count++))
fi

# Grafana
if docker compose ps grafana > /dev/null 2>&1; then
    echo -n "Grafana Status: "
    if check_service_status "grafana"; then
        ((healthy_count++))
    fi
    ((total_count++))
    
    if check_service "grafana" "curl -f http://localhost:3000/api/health" "Grafana"; then
        ((healthy_count++))
    fi
    ((total_count++))
fi

# Summary
echo -e "\n${BLUE}📈 Health Check Summary${NC}"
echo "=========================="
echo -e "Total Services Checked: ${total_count}"
echo -e "Healthy Services: ${GREEN}${healthy_count}${NC}"
echo -e "Unhealthy Services: ${RED}$((total_count - healthy_count))${NC}"

if [ $healthy_count -eq $total_count ]; then
    echo -e "\n${GREEN}🎉 All services are healthy!${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some services are unhealthy. Check the logs for details:${NC}"
    echo -e "   docker compose logs [service-name]"
    exit 1
fi 