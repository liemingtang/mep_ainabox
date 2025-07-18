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