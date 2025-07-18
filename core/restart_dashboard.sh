#!/bin/bash

# Script to rebuild and restart the dashboard container
# This ensures the dashboard runs properly in Docker with all the new features

set -e

echo "🔄 Rebuilding and restarting MDIS Dashboard..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Please run this script from the core directory."
    exit 1
fi

# Stop the dashboard container if it's running
echo "🛑 Stopping dashboard container..."
docker compose stop dashboard 2>/dev/null || echo "Dashboard container not running"

# Remove the dashboard container
echo "🗑️  Removing dashboard container..."
docker compose rm -f dashboard 2>/dev/null || echo "Dashboard container not found"

# Rebuild the dashboard image
echo "🔨 Rebuilding dashboard image..."
docker compose build dashboard

# Start the dashboard container
echo "🚀 Starting dashboard container..."
docker compose up -d dashboard

# Wait a moment for the container to start
echo "⏳ Waiting for dashboard to start..."
sleep 5

# Check if the dashboard is running
echo "🔍 Checking dashboard status..."
if docker compose ps dashboard | grep -q "Up"; then
    echo "✅ Dashboard is running successfully!"
    echo "🌐 Dashboard URL: http://localhost:8010"
    echo "📊 Service details: http://localhost:8010/service/file-watcher"
else
    echo "❌ Dashboard failed to start. Check logs with:"
    echo "   docker compose logs dashboard"
fi

echo ""
echo "📋 To view dashboard logs:"
echo "   docker compose logs -f dashboard"
echo ""
echo "🔧 To access dashboard shell:"
echo "   docker compose exec dashboard bash" 