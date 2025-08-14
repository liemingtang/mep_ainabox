#!/bin/bash

# MEP AI NABOX - Start Qdrant UI Daemon
# This script starts the Qdrant web interface as a background daemon

set -e

echo "🔍 Starting Qdrant UI Daemon..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$(dirname "$SCRIPT_DIR")"
QDANT_UI_DIR="$SERVICES_DIR/qdrant-ui"
LOG_FILE="$SERVICES_DIR/qdrant-ui.log"
PID_FILE="$SERVICES_DIR/qdrant-ui.pid"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker compose is not available. Please install Docker Compose first."
    exit 1
fi

# Load environment variables
echo "📋 Loading environment variables..."
if [ -f "$SERVICES_DIR/.env" ]; then
    echo "Loading services environment variables..."
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < "$SERVICES_DIR/.env"
else
    echo "⚠️  services/.env file not found. Using default values."
fi

# Check if Qdrant is running
if ! curl -s http://localhost:6333/ > /dev/null 2>&1; then
    echo "❌ Qdrant is not running. Please start Qdrant first:"
    echo "   docker compose up -d qdrant"
    exit 1
fi

# Cleanup existing Qdrant UI processes
echo "🧹 Cleaning up existing Qdrant UI processes..."

# Stop existing Qdrant UI container
if docker ps -q -f name=mep-qdrant-ui | grep -q .; then
    echo "⚠️  Found existing Qdrant UI container. Stopping..."
    docker stop mep-qdrant-ui || true
    docker rm mep-qdrant-ui || true
    sleep 3
fi

# Kill any existing Qdrant UI processes on host (fallback)
if pgrep -f "python3.*server.py" > /dev/null; then
    echo "⚠️  Found existing Qdrant UI process on host. Stopping..."
    pkill -f "python3.*server.py" || true
    sleep 3
fi

# Check if Qdrant UI is already running by container
if docker ps -q -f name=mep-qdrant-ui | grep -q .; then
    echo "✅ Qdrant UI container is already running"
    exit 0
fi

# Check if Qdrant UI is already running by PID file (fallback)
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Qdrant UI is already running (PID: $PID)"
        exit 0
    else
        echo "⚠️ Stale PID file found, removing..."
        rm -f "$PID_FILE"
    fi
fi

# Check if port 7070 is already in use
if netstat -tuln 2>/dev/null | grep -q ":7070 "; then
    echo "⚠️  Port 7070 is in use. Finding and stopping process..."
    PID=$(netstat -tulnp 2>/dev/null | grep ":7070 " | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        echo "🛑 Killing process $PID using port 7070..."
        kill "$PID" 2>/dev/null || true
        sleep 3
    fi
fi

# Build Qdrant UI Docker image if it doesn't exist
echo "🔨 Building Qdrant UI Docker image..."
cd "$QDANT_UI_DIR"
if ! docker images | grep -q "mep-qdrant-ui"; then
    echo "Building Qdrant UI image..."
    docker build -t mep-qdrant-ui .
else
    echo "Qdrant UI image already exists"
fi

# Start the Qdrant UI container
echo "🚀 Starting Qdrant UI container on http://localhost:7070"
echo "📁 Serving from: $QDANT_UI_DIR"
echo "📝 Logs will be written to: $LOG_FILE"

# Get Qdrant API key from environment
QDANT_API_KEY="${QDRANT_API_KEY:-}"
if [ -n "$QDANT_API_KEY" ]; then
    echo "🔑 Using Qdrant API key from environment"
    QDANT_UI_URL="http://localhost:7070/index.html?api_token=${QDANT_API_KEY}"
else
    echo "⚠️  No Qdrant API key found in environment"
    QDANT_UI_URL="http://localhost:7070/index.html"
fi

# Start the container
docker run -d \
    --name mep-qdrant-ui \
    --network mep-services-network \
    -p 7070:7070 \
    -v "$QDANT_UI_DIR:/app" \
    -e QDRANT_API_KEY="$QDANT_API_KEY" \
    mep-qdrant-ui

# Get container ID for PID file (for compatibility)
CONTAINER_ID=$(docker ps -q -f name=mep-qdrant-ui)
echo "$CONTAINER_ID" > "$PID_FILE"

# Wait a moment and check if it started successfully
sleep 3
if docker ps -q -f name=mep-qdrant-ui | grep -q .; then
    echo "✅ Qdrant UI container started successfully"
    echo "🔍 Access the UI at: $QDANT_UI_URL"
    
    # Test if the server is responding
    sleep 2
    if curl -s http://localhost:7070/index.html > /dev/null 2>&1; then
        echo "✅ Qdrant UI is responding to requests"
        echo "🔑 Full URL with API token: $QDANT_UI_URL"
    else
        echo "⚠️  Qdrant UI started but not responding to requests yet"
    fi
else
    echo "❌ Failed to start Qdrant UI container"
    rm -f "$PID_FILE"
    echo "📋 Check container logs with: docker logs mep-qdrant-ui"
    exit 1
fi 