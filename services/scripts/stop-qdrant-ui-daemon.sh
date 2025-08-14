#!/bin/bash

# MEP AI NABOX - Stop Qdrant UI Daemon
# This script stops the Qdrant web interface container

set -e

echo "🛑 Stopping Qdrant UI Daemon..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$SERVICES_DIR/qdrant-ui.pid"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Stop Qdrant UI container
echo "🛑 Stopping Qdrant UI container..."
if docker ps -q -f name=mep-qdrant-ui | grep -q .; then
    echo "Stopping mep-qdrant-ui container..."
    docker stop mep-qdrant-ui
    docker rm mep-qdrant-ui
    echo "✅ Qdrant UI container stopped and removed"
else
    echo "⚠️  Qdrant UI container not found"
fi

# Also stop any Qdrant UI processes running on host (fallback)
echo "🛑 Stopping Qdrant UI processes on host..."
if pgrep -f "python3.*server.py" > /dev/null; then
    echo "Stopping Qdrant UI process on host..."
    pkill -f "python3.*server.py" || true
    sleep 2
    echo "✅ Qdrant UI process on host stopped"
else
    echo "⚠️  No Qdrant UI process found on host"
fi

# Clean up stale PID files
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale Qdrant UI PID file..."
        rm -f "$PID_FILE"
        echo "✅ Stale PID file removed"
    fi
fi

echo ""
echo "🎉 Qdrant UI stopped successfully!"
echo "================================"
echo ""
echo "📊 To restart the Qdrant UI:"
echo "  ./scripts/start-qdrant-ui-daemon.sh"
echo "" 