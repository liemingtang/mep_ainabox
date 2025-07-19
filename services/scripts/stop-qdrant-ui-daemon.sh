#!/bin/bash

# MEP AI NABOX - Stop Qdrant UI Daemon
# This script stops the Qdrant web interface daemon

set -e

echo "🛑 Stopping Qdrant UI Daemon..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$SERVICES_DIR/qdrant-ui.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️ No PID file found. Qdrant UI may not be running."
    exit 0
fi

# Read PID from file
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️ Process $PID is not running. Removing stale PID file."
    rm -f "$PID_FILE"
    exit 0
fi

# Kill the process
echo "🔍 Stopping Qdrant UI process (PID: $PID)..."
kill "$PID"

# Wait for process to stop
sleep 2

# Check if process stopped
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️ Process did not stop gracefully. Force killing..."
    kill -9 "$PID"
    sleep 1
fi

# Remove PID file
rm -f "$PID_FILE"

echo "✅ Qdrant UI stopped successfully" 