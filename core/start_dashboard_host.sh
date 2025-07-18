#!/bin/bash

# Dashboard Host Startup Script
# This script runs the dashboard service directly on the host

set -e

# Parse command line arguments
BACKGROUND_MODE=false
if [[ "$1" == "--background" ]]; then
    BACKGROUND_MODE=true
fi

if [ "$BACKGROUND_MODE" = false ]; then
    echo "🚀 Starting MEP AI NABOX Dashboard on host..."
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="$SCRIPT_DIR/dashboard"

if [ "$BACKGROUND_MODE" = false ]; then
    echo "📍 Dashboard directory: $DASHBOARD_DIR"
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [ "$BACKGROUND_MODE" = false ]; then
    echo "🐍 Python version: $PYTHON_VERSION"
fi

# Create virtual environment if it doesn't exist
VENV_DIR="$DASHBOARD_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    if [ "$BACKGROUND_MODE" = false ]; then
        echo "📦 Creating virtual environment..."
    fi
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
if [ "$BACKGROUND_MODE" = false ]; then
    echo "🔧 Activating virtual environment..."
fi
source "$VENV_DIR/bin/activate"

# Install dependencies
if [ "$BACKGROUND_MODE" = false ]; then
    echo "📥 Installing dependencies..."
fi
pip install --upgrade pip > /dev/null 2>&1
pip install -r "$DASHBOARD_DIR/requirements.txt" > /dev/null 2>&1

# Set environment variables
export CORE_PROCESSOR_URL=http://localhost:8001
export FILE_WATCHER_URL=http://localhost:8009
export STORAGE_MANAGER_URL=http://localhost:8004
export ELASTICSEARCH_URL=http://localhost:9200
export QDRANT_URL=http://localhost:6333
export NEO4J_URL=http://localhost:7474
export QDRANT_API_KEY=qdrant_api_key
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=neo4j_password

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

if [ "$BACKGROUND_MODE" = false ]; then
    echo "🌐 Starting dashboard service on http://localhost:8010"
    echo "📊 Dashboard: http://localhost:8010"
    echo "⚙️  Admin Panel: http://localhost:8010/admin"
    echo ""
    echo "Press Ctrl+C to stop the dashboard"
fi

# Start the dashboard service
cd "$DASHBOARD_DIR"

if [ "$BACKGROUND_MODE" = true ]; then
    # Run in background and redirect output to log file
    nohup python3 main.py > "$SCRIPT_DIR/logs/dashboard.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/dashboard.pid"
else
    # Run in foreground
    python3 main.py
fi 