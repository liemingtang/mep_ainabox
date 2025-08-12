#!/bin/bash

# MDIS Dashboard Startup Script
# This script starts the dashboard with proper configuration and dependencies

set -e

echo "🚀 Starting MDIS Dashboard..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the dashboard directory."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p config
mkdir -p static/css
mkdir -p static/js

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Warning: Docker is not running. Some features may not work properly."
    echo "   The dashboard will still work but logs and metrics from containers may not be available."
fi

# Check if required Python packages are installed
echo "🔍 Checking Python dependencies..."
python3 -c "import fastapi, httpx, jinja2" 2>/dev/null || {
    echo "📦 Installing required Python packages..."
    pip3 install fastapi uvicorn httpx jinja2 python-multipart
}

# Check if services are running (optional)
echo "🔍 Checking if MEP services are running..."
SERVICES=("mep-core-processor" "mep-elasticsearch" "mep-qdrant" "mep-neo4j")
RUNNING_SERVICES=0

for service in "${SERVICES[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
        echo "✅ $service is running"
        ((RUNNING_SERVICES++))
    else
        echo "❌ $service is not running"
    fi
done

if [ $RUNNING_SERVICES -eq 0 ]; then
    echo "⚠️  Warning: No MEP services are running."
    echo "   Start the services first with: cd ../.. && docker compose up -d"
fi

# Set environment variables
export CORE_PROCESSOR_URL=${CORE_PROCESSOR_URL:-"http://localhost:8001"}
export FILE_WATCHER_URL=${FILE_WATCHER_URL:-"http://localhost:8009"}
export STORAGE_MANAGER_URL=${STORAGE_MANAGER_URL:-"http://localhost:8004"}
export ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-"http://localhost:9200"}
export QDRANT_URL=${QDRANT_URL:-"http://localhost:6333"}
export NEO4J_URL=${NEO4J_URL:-"http://localhost:7474"}
export HUGGINGFACE_EMBEDDING_URL=${HUGGINGFACE_EMBEDDING_URL:-"http://localhost:8082"}

echo "🌐 Dashboard will be available at: http://localhost:8010"
echo "📊 API endpoints will be available at: http://localhost:8010/api/"

# Start the dashboard
echo "🚀 Starting dashboard server..."
echo "   Press Ctrl+C to stop the dashboard"
echo ""

python3 main.py 