#!/bin/bash

# MEP AI NABOX - Native Service Startup Script
# This script starts all core processing services directly on the system without Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR"
LOGS_DIR="$CORE_DIR/logs"
CONFIG_DIR="$CORE_DIR/config"
PYTHON_PATH="$CORE_DIR"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Function to show help
show_help() {
    echo "MEP AI NABOX - Native Service Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [SERVICES]"
    echo ""
    echo "This script starts core processing services directly on the system without Docker."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help              Show this help message"
    echo "  --stop                   Stop all running services"
    echo "  --restart                Restart all services"
    echo "  --status                 Show status of all services"
    echo "  --logs [SERVICE]         Show logs for a specific service"
    echo ""
    echo "SERVICES:"
    echo "  api-gateway              API Gateway (port 8011)"
    echo "  core-processor           Core Processor (port 8001)"
    echo "  document-router          Document Router (port 8002)"
    echo "  processing-pipeline      Processing Pipeline (port 8003)"
    echo "  storage-manager          Storage Manager (port 8004)"
    echo "  text-processor           Text Processor (port 8005)"
    echo "  metadata-processor       Metadata Processor (port 8006)"
    echo "  embedding-processor      Embedding Processor (port 8007)"
    echo "  entity-processor         Entity Processor (port 8008)"
    echo "  queue-worker             Queue Worker (background)"
    echo "  status-worker            Status Worker (background)"
    echo "  file-watcher             File Watcher (background)"
    echo "  all                      All services (default)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                      # Start all services"
    echo "  $0 core-processor       # Start only core processor"
    echo "  $0 --stop               # Stop all services"
    echo "  $0 --status             # Show service status"
    echo "  $0 --logs text-processor # Show text processor logs"
}

# Function to check if a service is running
is_service_running() {
    local service_name=$1
    local pid_file="$LOGS_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    local main_file=$4
    local pid_file="$LOGS_DIR/${service_name}.pid"
    local log_file="$LOGS_DIR/${service_name}.log"
    
    echo -e "${BLUE}🚀 Starting $service_name...${NC}"
    
    if is_service_running "$service_name"; then
        echo -e "${YELLOW}⚠️  $service_name is already running${NC}"
        return 0
    fi
    
    # Load environment variables from file
    if [ -f "$CORE_DIR/env.native" ]; then
        export $(cat "$CORE_DIR/env.native" | grep -v '^#' | xargs)
    fi
    
    # Set environment variables
    export CONFIG_PATH="$CONFIG_DIR"
    export PYTHONPATH="$PYTHON_PATH:$PYTHONPATH"
    
    # Service-specific environment variables
    case $service_name in
        "api-gateway")
            export CORE_SERVICE_URL="http://localhost:8001"
            export DOCUMENT_ROUTER_URL="http://localhost:8002"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export STORAGE_MANAGER_URL="http://localhost:8004"
            ;;
        "core-processor")
            export DOCUMENT_ROUTER_URL="http://localhost:8002"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export POSTGRES_HOST="localhost"
            export ELASTICSEARCH_HOST="localhost"
            export QDRANT_HOST="localhost"
            export NEO4J_HOST="localhost"
            export MINIO_HOST="localhost"
            export REDIS_HOST="localhost"
            ;;
        "processing-pipeline")
            export PROCESSING_PIPELINE_PORT="8003"
            export CORE_PROCESSOR_URL="http://localhost:8001"
            export STORAGE_MANAGER_URL="http://localhost:8004"
            export TEXT_PROCESSOR_URL="http://localhost:8005"
            export EMBEDDING_PROCESSOR_URL="http://localhost:8007"
            export DYNAMIC_TEXT_PROCESSOR_SCRIPT="$CORE_DIR/text_processor_dynamic.sh"
            export EMBEDDING_PROVIDER="huggingface"
            ;;
        "text-processor")
            export TEXT_PROCESSOR_PORT="8005"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export CORE_PROCESSOR_URL="http://localhost:8001"
            ;;
        "metadata-processor")
            export METADATA_PROCESSOR_PORT="8006"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export CORE_PROCESSOR_URL="http://localhost:8001"
            ;;
        "embedding-processor")
            export EMBEDDING_PROCESSOR_PORT="8007"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export CORE_PROCESSOR_URL="http://localhost:8001"
            ;;
        "entity-processor")
            export ENTITY_PROCESSOR_PORT="8008"
            export PROCESSING_PIPELINE_URL="http://localhost:8003"
            export CORE_PROCESSOR_URL="http://localhost:8001"
            ;;
        "storage-manager")
            export STORAGE_MANAGER_PORT="8004"
            export POSTGRES_HOST="localhost"
            export ELASTICSEARCH_HOST="localhost"
            export QDRANT_HOST="localhost"
            export NEO4J_HOST="localhost"
            export MINIO_HOST="localhost"
            export REDIS_HOST="localhost"
            ;;
    esac
    
    # Start the service
    cd "$service_dir"
    nohup python3 "$main_file" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    # Wait a moment for service to start
    sleep 2
    
    # Check if service started successfully
    if is_service_running "$service_name"; then
        echo -e "${GREEN}✅ $service_name started successfully (PID: $pid)${NC}"
        if [ -n "$port" ]; then
            echo -e "${CYAN}   Service available at: http://localhost:$port${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to start $service_name${NC}"
        echo -e "${YELLOW}   Check logs: $log_file${NC}"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$LOGS_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo -e "${YELLOW}🛑 Stopping $service_name (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null || true
        rm -f "$pid_file"
        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  $service_name is not running${NC}"
    fi
}

# Function to show service status
show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo "=================================="
    
    local services=(
        "api-gateway:8011"
        "core-processor:8001"
        "document-router:8002"
        "processing-pipeline:8003"
        "storage-manager:8004"
        "text-processor:8005"
        "metadata-processor:8006"
        "embedding-processor:8007"
        "entity-processor:8008"
        "queue-worker:"
        "status-worker:"
        "file-watcher:"
    )
    
    for service_info in "${services[@]}"; do
        local service_name=$(echo "$service_info" | cut -d: -f1)
        local port=$(echo "$service_info" | cut -d: -f2)
        
        if is_service_running "$service_name"; then
            local pid=$(cat "$LOGS_DIR/${service_name}.pid")
            echo -e "${GREEN}✅ $service_name (PID: $pid)${NC}"
            if [ -n "$port" ]; then
                echo -e "   Port: $port"
            fi
        else
            echo -e "${RED}❌ $service_name (not running)${NC}"
        fi
    done
}

# Function to show logs
show_logs() {
    local service_name=$1
    local log_file="$LOGS_DIR/${service_name}.log"
    
    if [ -f "$log_file" ]; then
        echo -e "${BLUE}📋 Logs for $service_name:${NC}"
        echo "=================================="
        tail -f "$log_file"
    else
        echo -e "${RED}❌ No log file found for $service_name${NC}"
    fi
}

# Parse command line arguments
ACTION="start"
SERVICES=()
SHOW_LOGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --logs)
            ACTION="logs"
            SHOW_LOGS="$2"
            shift 2
            ;;
        *)
            SERVICES+=("$1")
            shift
            ;;
    esac
done

# Default to all services if none specified
if [ ${#SERVICES[@]} -eq 0 ]; then
    SERVICES=("all")
fi

# Service definitions
declare -A SERVICE_CONFIGS=(
    ["api-gateway"]="$CORE_DIR/api_gateway:8011:main.py"
    ["core-processor"]="$CORE_DIR/core_processor:8001:main.py"
    ["document-router"]="$CORE_DIR/document_router:8002:main.py"
    ["processing-pipeline"]="$CORE_DIR/processing_pipeline:8003:main.py"
    ["storage-manager"]="$CORE_DIR/storage_manager:8004:main.py"
    ["text-processor"]="$CORE_DIR/processors/text_processor:8005:main.py"
    ["metadata-processor"]="$CORE_DIR/processors/metadata_processor:8006:main.py"
    ["embedding-processor"]="$CORE_DIR/processors/embedding_processor:8007:main.py"
    ["entity-processor"]="$CORE_DIR/processors/entity_processor:8008:main.py"
    ["queue-worker"]="$CORE_DIR/processing_pipeline::queue_worker.py"
    ["status-worker"]="$CORE_DIR/processing_pipeline::status_worker.py"
    ["file-watcher"]="$CORE_DIR/file_watcher::main.py"
)

# Handle different actions
case $ACTION in
    "start")
        echo -e "${BLUE}🚀 Starting MEP AI NABOX Native Services${NC}"
        echo "================================================"
        
        for service in "${SERVICES[@]}"; do
            if [ "$service" = "all" ]; then
                for service_name in "${!SERVICE_CONFIGS[@]}"; do
                    config="${SERVICE_CONFIGS[$service_name]}"
                    dir=$(echo "$config" | cut -d: -f1)
                    port=$(echo "$config" | cut -d: -f2)
                    main_file=$(echo "$config" | cut -d: -f3)
                    start_service "$service_name" "$dir" "$port" "$main_file"
                done
            else
                if [[ -n "${SERVICE_CONFIGS[$service]}" ]]; then
                    config="${SERVICE_CONFIGS[$service]}"
                    dir=$(echo "$config" | cut -d: -f1)
                    port=$(echo "$config" | cut -d: -f2)
                    main_file=$(echo "$config" | cut -d: -f3)
                    start_service "$service" "$dir" "$port" "$main_file"
                else
                    echo -e "${RED}❌ Unknown service: $service${NC}"
                fi
            fi
        done
        
        echo -e "${GREEN}🎉 All services started successfully!${NC}"
        echo -e "${CYAN}📊 Use '$0 --status' to check service status${NC}"
        echo -e "${CYAN}📋 Use '$0 --logs [service]' to view logs${NC}"
        ;;
        
    "stop")
        echo -e "${YELLOW}🛑 Stopping MEP AI NABOX Native Services${NC}"
        echo "================================================"
        
        for service in "${SERVICES[@]}"; do
            if [ "$service" = "all" ]; then
                for service_name in "${!SERVICE_CONFIGS[@]}"; do
                    stop_service "$service_name"
                done
            else
                stop_service "$service"
            fi
        done
        
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;
        
    "restart")
        echo -e "${BLUE}🔄 Restarting MEP AI NABOX Native Services${NC}"
        echo "================================================"
        
        for service in "${SERVICES[@]}"; do
            if [ "$service" = "all" ]; then
                for service_name in "${!SERVICE_CONFIGS[@]}"; do
                    stop_service "$service_name"
                    sleep 1
                    config="${SERVICE_CONFIGS[$service_name]}"
                    dir=$(echo "$config" | cut -d: -f1)
                    port=$(echo "$config" | cut -d: -f2)
                    main_file=$(echo "$config" | cut -d: -f3)
                    start_service "$service_name" "$dir" "$port" "$main_file"
                done
            else
                stop_service "$service"
                sleep 1
                if [[ -n "${SERVICE_CONFIGS[$service]}" ]]; then
                    config="${SERVICE_CONFIGS[$service]}"
                    dir=$(echo "$config" | cut -d: -f1)
                    port=$(echo "$config" | cut -d: -f2)
                    main_file=$(echo "$config" | cut -d: -f3)
                    start_service "$service" "$dir" "$port" "$main_file"
                fi
            fi
        done
        
        echo -e "${GREEN}✅ All services restarted${NC}"
        ;;
        
    "status")
        show_status
        ;;
        
    "logs")
        if [ -n "$SHOW_LOGS" ]; then
            show_logs "$SHOW_LOGS"
        else
            echo -e "${RED}❌ Please specify a service name for logs${NC}"
            echo -e "${CYAN}   Usage: $0 --logs [service-name]${NC}"
        fi
        ;;
esac 