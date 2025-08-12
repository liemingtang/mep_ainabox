#!/bin/bash

# MEP AI NABOX Admin Startup Script
# This script starts only the dashboard first, allowing admin control via web interface

set -e

echo "🚀 MEP AI NABOX - Admin Startup Mode"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "core/docker-compose.yml" ]; then
    echo "❌ Error: core/docker-compose.yml not found. Please run this script from the mep_ainabox root directory."
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running. Please start Docker first."
    exit 1
fi

# Cleanup existing admin UI services
echo "🧹 Cleaning up existing admin UI services..."
echo "📋 Checking for existing processes..."

# Kill existing dashboard processes
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️  Found existing dashboard process. Stopping..."
    pkill -f "python3.*main.py" || true
    sleep 2
fi

# Kill existing Qdrant UI processes
if pgrep -f "python3.*server.py" > /dev/null; then
    echo "⚠️  Found existing Qdrant UI process. Stopping..."
    pkill -f "python3.*server.py" || true
    sleep 2
fi

# Clean up stale PID files
if [ -f "services/qdrant-ui.pid" ]; then
    PID=$(cat services/qdrant-ui.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "🧹 Removing stale Qdrant UI PID file..."
        rm -f services/qdrant-ui.pid
    fi
fi

if [ -f "core/dashboard.pid" ]; then
    PID=$(cat core/dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "🧹 Removing stale dashboard PID file..."
        rm -f core/dashboard.pid
    fi
fi

# Check if ports are in use and kill processes using them
echo "🔍 Checking for processes using admin UI ports..."

# Check port 8010 (dashboard)
if netstat -tuln 2>/dev/null | grep -q ":8010 "; then
    echo "⚠️  Port 8010 is in use. Finding and stopping process..."
    PID=$(netstat -tulnp 2>/dev/null | grep ":8010 " | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        kill "$PID" 2>/dev/null || true
        sleep 2
    fi
fi

# Check port 7070 (Qdrant UI)
if netstat -tuln 2>/dev/null | grep -q ":7070 "; then
    echo "⚠️  Port 7070 is in use. Finding and stopping process..."
    PID=$(netstat -tulnp 2>/dev/null | grep ":7070 " | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        kill "$PID" 2>/dev/null || true
        sleep 2
    fi
fi

echo "✅ Cleanup completed!"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p core/documents core/processed core/temp core/logs core/watch_folder
mkdir -p services/volumes services/config

# Set permissions (ignore errors for read-only files)
chmod -R 755 core/documents core/temp core/logs core/watch_folder 2>/dev/null || true
chmod -R 755 core/processed 2>/dev/null || true

# Load environment variables for core
if [ -f "core/.env" ]; then
    echo "📋 Loading core environment variables..."
    # Load only valid environment variable lines
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            # Check if it's a valid environment variable assignment
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < core/.env
else
    echo "⚠️  Warning: core/.env file not found. Using default values."
fi

# Load environment variables for services
if [ -f "services/.env" ]; then
    echo "📋 Loading services environment variables..."
    # Load only valid environment variable lines
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            # Check if it's a valid environment variable assignment
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < services/.env
else
    echo "⚠️  Warning: services/.env file not found. Using default values."
fi

# Create Docker network if it doesn't exist
echo "🌐 Setting up Docker network..."
if ! docker network ls | grep -q "mep-services-network"; then
    echo "Creating mep-services-network..."
    docker network create mep-services-network
else
    echo "Network mep-services-network already exists."
fi

# Start infrastructure services for admin mode
echo "🔧 Starting infrastructure services for admin mode..."
cd services

# Start essential services for admin functionality
echo "🚀 Starting PostgreSQL, Qdrant, and HuggingFace Embeddings..."
docker compose up -d postgres qdrant huggingface-embeddings

# Wait for infrastructure services to be ready
echo "⏳ Waiting for infrastructure services to start..."
sleep 30

# Check infrastructure services health
echo "🔍 Checking infrastructure services health..."

# PostgreSQL health check
if docker compose exec -T postgres pg_isready -U mep_user -d mep_ainabox > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "⚠️  PostgreSQL is starting..."
fi

# Qdrant health check
if curl -f http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant is ready"
else
    echo "⚠️  Qdrant is starting..."
fi

    # HuggingFace Embeddings health check
    if curl -f http://localhost:8082/ > /dev/null 2>&1; then
        echo "✅ HuggingFace Embeddings is ready"
    else
        echo "⚠️  HuggingFace Embeddings is starting..."
    fi

cd ..

# Start only the dashboard service on host
echo "🎛️  Starting Dashboard (Admin Interface) on host..."
cd core

# Check if dashboard is already running
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️  Dashboard is already running. Stopping and restarting..."
    pkill -f "python3.*main.py" || true
    sleep 2
fi

# Start dashboard on host using the dedicated script in background mode
echo "🚀 Starting dashboard on host..."
./start_dashboard_host.sh --background

# Wait for dashboard to be ready
echo "⏳ Waiting for dashboard to start..."
sleep 10

# Check if dashboard is healthy
echo "🔍 Checking dashboard health..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
        echo "✅ Dashboard is ready!"
        break
    else
        echo "⏳ Waiting for dashboard... (attempt $((attempt + 1))/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Dashboard failed to start properly."
    echo "Check logs with: tail -f logs/app.log"
    exit 1
fi

cd ..

echo ""
echo "🎉 Admin Dashboard Started Successfully!"
echo "========================================"
echo ""
echo "🌐 Dashboard URL: http://localhost:8010"
echo "🔧 Admin Panel: http://localhost:8010/admin"
echo "🧠 HuggingFace Embeddings: http://localhost:8082"
echo ""
echo "📋 Next Steps:"
echo "1. Open http://localhost:8010 in your browser"
echo "2. Go to the Admin panel"
echo "3. Use the 'Start All Services' button to launch infrastructure and core services"
echo "4. Monitor the startup process in real-time"
echo ""
echo "📊 Available Commands:"
echo "  View dashboard logs: tail -f core/logs/dashboard.log"
echo "  Stop dashboard: cd core && ./stop_dashboard_host.sh"
echo "  Restart dashboard: ./start_admin.sh"
echo ""
echo "🔍 To check what's running:"
echo "  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo "" 