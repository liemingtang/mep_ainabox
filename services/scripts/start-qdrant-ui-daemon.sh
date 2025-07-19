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

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if Qdrant is running
if ! curl -s http://localhost:6333/ > /dev/null 2>&1; then
    echo "❌ Qdrant is not running. Please start Qdrant first:"
    echo "   docker compose up -d qdrant"
    exit 1
fi

# Check if Qdrant UI is already running
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
    echo "❌ Port 7070 is already in use"
    exit 1
fi

# Change to the qdrant-ui directory
cd "$QDANT_UI_DIR"

# Start the web server in background
echo "🚀 Starting Qdrant UI server on http://localhost:7070"
echo "📁 Serving from: $(pwd)"
echo "📝 Logs will be written to: $LOG_FILE"

# Start the server in background and capture PID
nohup python3 server.py > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID to file
echo "$PID" > "$PID_FILE"

# Wait a moment and check if it started successfully
sleep 2
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Qdrant UI started successfully (PID: $PID)"
    echo "🔍 Access the UI at: http://localhost:7070/index.html"
else
    echo "❌ Failed to start Qdrant UI"
    rm -f "$PID_FILE"
    exit 1
fi 