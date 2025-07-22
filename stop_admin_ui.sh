#!/bin/bash

# MEP AI NABOX - Stop Admin UI Services
# This script stops all admin UI services cleanly

set -e

echo "🛑 MEP AI NABOX - Stopping Admin UI Services"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "core/docker-compose.yml" ]; then
    echo "❌ Error: core/docker-compose.yml not found. Please run this script from the mep_ainabox root directory."
    exit 1
fi

echo "🧹 Cleaning up admin UI services..."

# Stop dashboard processes
echo "📋 Checking for dashboard processes..."
if pgrep -f "python3.*main.py" > /dev/null; then
    echo "🛑 Stopping dashboard process..."
    pkill -f "python3.*main.py" || true
    sleep 2
else
    echo "ℹ️  No dashboard process found"
fi

# Stop Qdrant UI processes
echo "📋 Checking for Qdrant UI processes..."
if pgrep -f "python3.*server.py" > /dev/null; then
    echo "🛑 Stopping Qdrant UI process..."
    pkill -f "python3.*server.py" || true
    sleep 2
else
    echo "ℹ️  No Qdrant UI process found"
fi

# Clean up PID files
echo "🧹 Cleaning up PID files..."

if [ -f "core/dashboard.pid" ]; then
    PID=$(cat core/dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "🧹 Removing stale dashboard PID file..."
        rm -f core/dashboard.pid
    else
        echo "⚠️  Dashboard PID file still valid, process may still be running"
    fi
fi

if [ -f "services/qdrant-ui.pid" ]; then
    PID=$(cat services/qdrant-ui.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "🧹 Removing stale Qdrant UI PID file..."
        rm -f services/qdrant-ui.pid
    else
        echo "⚠️  Qdrant UI PID file still valid, process may still be running"
    fi
fi

# Check if ports are still in use
echo "🔍 Checking if admin UI ports are still in use..."

if netstat -tuln 2>/dev/null | grep -q ":8010 "; then
    echo "⚠️  Port 8010 (dashboard) is still in use"
    PID=$(netstat -tulnp 2>/dev/null | grep ":8010 " | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        echo "🛑 Force killing process $PID on port 8010..."
        kill -9 "$PID" 2>/dev/null || true
    fi
else
    echo "✅ Port 8010 (dashboard) is free"
fi

if netstat -tuln 2>/dev/null | grep -q ":7070 "; then
    echo "⚠️  Port 7070 (Qdrant UI) is still in use"
    PID=$(netstat -tulnp 2>/dev/null | grep ":7070 " | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        echo "🛑 Force killing process $PID on port 7070..."
        kill -9 "$PID" 2>/dev/null || true
    fi
else
    echo "✅ Port 7070 (Qdrant UI) is free"
fi

# Final verification
echo ""
echo "🔍 Final verification..."
sleep 2

if pgrep -f "python3.*main.py" > /dev/null; then
    echo "⚠️  Dashboard process is still running"
else
    echo "✅ Dashboard process stopped"
fi

if pgrep -f "python3.*server.py" > /dev/null; then
    echo "⚠️  Qdrant UI process is still running"
else
    echo "✅ Qdrant UI process stopped"
fi

if netstat -tuln 2>/dev/null | grep -q ":8010 "; then
    echo "⚠️  Port 8010 is still in use"
else
    echo "✅ Port 8010 is free"
fi

if netstat -tuln 2>/dev/null | grep -q ":7070 "; then
    echo "⚠️  Port 7070 is still in use"
else
    echo "✅ Port 7070 is free"
fi

echo ""
echo "🎉 Admin UI services cleanup completed!"
echo "========================================"
echo ""
echo "📋 To restart admin services:"
echo "  ./start_admin.sh"
echo ""
echo "📋 To check what's running:"
echo "  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo "  netstat -tuln | grep -E ':(8010|7070)'"
echo "" 