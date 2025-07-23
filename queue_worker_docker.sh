#!/bin/bash

# Docker-based Queue Worker for MEP AI NABOX
# Runs the queue worker in a Docker container

set -e

# Configuration
CONTAINER_NAME="mep-queue-worker"
IMAGE_NAME="mep-file-watcher:latest"
NETWORK_NAME="mep-ainabox_default"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Docker Queue Worker for MEP AI NABOX"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  start       Start the queue worker container"
    echo "  stop        Stop the queue worker container"
    echo "  restart     Restart the queue worker container"
    echo "  status      Show container status"
    echo "  logs        Show container logs"
    echo "  test        Run queue worker in test mode"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start queue worker in background"
    echo "  $0 stop      # Stop queue worker"
    echo "  $0 status    # Check if running"
    echo "  $0 test      # Test processing one job"
    echo ""
}

# Function to check if container exists
container_exists() {
    docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"
}

# Function to check if container is running
container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"
}

# Function to start queue worker
start_worker() {
    print_info "Starting queue worker container..."
    
    if container_running; then
        print_warning "Queue worker is already running"
        return 0
    fi
    
    # Remove existing container if it exists
    if container_exists; then
        print_info "Removing existing container..."
        docker rm "$CONTAINER_NAME" > /dev/null 2>&1 || true
    fi
    
    # Start the container
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK_NAME" \
        --restart unless-stopped \
        -e CORE_PROCESSOR_URL=http://core-processor:8001 \
        -e PROCESSING_PIPELINE_URL=http://processing-pipeline:8003 \
        "$IMAGE_NAME" \
        python3 /app/queue_worker.py
    
    if container_running; then
        print_status "Queue worker started successfully"
        print_info "Container ID: $(docker ps -q --filter name=$CONTAINER_NAME)"
    else
        print_error "Failed to start queue worker"
        return 1
    fi
}

# Function to stop queue worker
stop_worker() {
    print_info "Stopping queue worker container..."
    
    if ! container_running; then
        print_warning "Queue worker is not running"
        return 0
    fi
    
    docker stop "$CONTAINER_NAME"
    print_status "Queue worker stopped"
}

# Function to restart queue worker
restart_worker() {
    print_info "Restarting queue worker container..."
    stop_worker
    sleep 2
    start_worker
}

# Function to show status
show_status() {
    print_info "Queue worker status:"
    
    if container_running; then
        print_status "✅ Running"
        echo "Container ID: $(docker ps -q --filter name=$CONTAINER_NAME)"
        echo "Started: $(docker inspect --format='{{.State.StartedAt}}' $CONTAINER_NAME 2>/dev/null || echo 'Unknown')"
        echo "Status: $(docker inspect --format='{{.State.Status}}' $CONTAINER_NAME 2>/dev/null || echo 'Unknown')"
    elif container_exists; then
        print_warning "⚠️  Stopped"
        echo "Container exists but not running"
    else
        print_error "❌ Not found"
        echo "No queue worker container found"
    fi
}

# Function to show logs
show_logs() {
    if container_exists; then
        print_info "Queue worker logs:"
        docker logs "$CONTAINER_NAME" --tail 50 -f
    else
        print_error "Queue worker container not found"
        return 1
    fi
}

# Function to test queue worker
test_worker() {
    print_info "Testing queue worker..."
    
    if ! container_running; then
        print_warning "Queue worker not running, starting for test..."
        start_worker
        sleep 3
    fi
    
    # Run test command
    docker exec "$CONTAINER_NAME" python3 /app/queue_worker.py --test
}

# Main function
main() {
    case "${1:-}" in
        start)
            start_worker
            ;;
        stop)
            stop_worker
            ;;
        restart)
            restart_worker
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        test)
            test_worker
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 