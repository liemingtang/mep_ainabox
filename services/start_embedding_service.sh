#!/bin/bash

# HuggingFace Embedding Service Startup Script for mep_ainabox
# This script starts the embedding service independently or as part of the main system

set -e

echo "Starting HuggingFace Embedding Service for mep_ainabox..."

# Check if docker-compose is available
if ! command -v docker compose &> /dev/null; then
    echo "Error: docker compose is not installed or not in PATH"
    exit 1
fi

# Function to start just the embedding service
start_embedding_only() {
    echo "Starting embedding service only..."
    docker compose up -d huggingface-embeddings
    echo "Embedding service started on port 8082"
    echo "Health check: http://localhost:8082/"
}

# Function to start all services
start_all_services() {
    echo "Starting all mep_ainabox services..."
    docker compose up -d
    echo "All services started"
}

# Function to check service status
check_status() {
    echo "Checking service status..."
    docker compose ps huggingface-embeddings
}

# Function to view logs
view_logs() {
    echo "Viewing embedding service logs..."
    docker compose logs -f huggingface-embeddings
}

# Function to stop services
stop_services() {
    echo "Stopping services..."
    if [ "$1" = "embedding" ]; then
        docker compose stop huggingface-embeddings
        echo "Embedding service stopped"
    else
        docker compose down
        echo "All services stopped"
    fi
}

# Main script logic
case "${1:-start}" in
    "start")
        start_embedding_only
        ;;
    "all")
        start_all_services
        ;;
    "status")
        check_status
        ;;
    "logs")
        view_logs
        ;;
    "stop")
        stop_services "${2:-all}"
        ;;
    "restart")
        stop_services "embedding"
        sleep 2
        start_embedding_only
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start     - Start embedding service only (default)"
        echo "  all       - Start all services"
        echo "  status    - Check service status"
        echo "  logs      - View embedding service logs"
        echo "  stop      - Stop services [embedding|all]"
        echo "  restart   - Restart embedding service"
        echo "  help      - Show this help message"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
