#!/bin/bash

# MEP AI NABOX - Start Qdrant UI
# This script starts the Qdrant web interface

set -e

echo "🔍 Starting Qdrant UI..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if Qdrant is running
if ! curl -s http://localhost:6333/ > /dev/null; then
    echo "❌ Qdrant is not running. Please start Qdrant first:"
    echo "   docker compose up -d qdrant"
    exit 1
fi

# Change to the qdrant-ui directory
cd "$(dirname "$0")/../qdrant-ui"

# Start the web server
echo "🚀 Starting Qdrant UI server on http://localhost:7070"
echo "📁 Serving from: $(pwd)"
echo "🔍 Access the UI at: http://localhost:7070/index.html"
echo "Press Ctrl+C to stop the server"
echo ""

python3 server.py 