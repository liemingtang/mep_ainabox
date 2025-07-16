#!/bin/bash

# Startup script for the Core System
set -e

echo "Starting Core System..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found. Please run this script from the core directory."
    exit 1
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p documents processed temp logs watch_folder

# Set permissions
chmod -R 755 documents processed temp logs watch_folder

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker first."
    exit 1
fi

# Check if infrastructure services are running
echo "Checking if infrastructure services are running..."
if ! docker network ls | grep -q "mep-services-network"; then
    echo "Warning: Infrastructure services network not found."
    echo "Attempting to start infrastructure services..."
    cd ../services
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d
        cd ../core
        echo "Waiting for infrastructure services to be ready..."
        sleep 30
    else
        echo "Error: Infrastructure services docker-compose.yml not found."
        echo "Please ensure the services directory contains the required files."
        exit 1
    fi
fi

# Load environment variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    # Load environment variables safely, ignoring lines with spaces in values
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            # Only export lines that look like valid environment variables
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < .env
else
    echo "Warning: .env file not found. Using default values."
fi

# Start the core system
echo "Starting core system services..."
docker compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo "Checking service health..."
sleep 5  # Give services a bit more time to start

for service in api-gateway core-processor document-router processing-pipeline storage-manager; do
    echo "Checking $service..."
    # Try different ports for different services
    port=8000
    case $service in
        "api-gateway") port=8000 ;;
        "core-processor") port=8001 ;;
        "document-router") port=8002 ;;
        "processing-pipeline") port=8003 ;;
        "storage-manager") port=8004 ;;
    esac
    
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        echo "$service is healthy (port $port)"
    else
        echo "Warning: $service health check failed (port $port)"
        echo "You can check logs with: docker-compose logs $service"
    fi
done

echo "Core System started successfully!"
echo ""
echo "Services available at:"
echo "- API Gateway: http://localhost:8000"
echo "- Core Processor: http://localhost:8001"
echo "- Document Router: http://localhost:8002"
echo "- Processing Pipeline: http://localhost:8003"
echo "- Storage Manager: http://localhost:8004"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down" 