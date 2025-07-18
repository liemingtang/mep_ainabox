#!/bin/bash

# Dashboard Host Stop Script
# This script stops the dashboard service running on the host

set -e

echo "🛑 Stopping MEP AI NABOX Dashboard..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/dashboard.pid"

# Check if dashboard is running
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "🔄 Stopping dashboard process..."
    
    # Try to stop gracefully first
    pkill -f "python3.*main.py" || true
    
    # Wait a moment
    sleep 2
    
    # Force kill if still running
    if pgrep -f "python3.*main.py" > /dev/null; then
        echo "⚠️  Force stopping dashboard..."
        pkill -9 -f "python3.*main.py" || true
    fi
    
    # Remove PID file if it exists
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
    fi
    
    echo "✅ Dashboard stopped successfully"
else
    echo "ℹ️  Dashboard is not running"
fi 