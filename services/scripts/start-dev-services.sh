#!/bin/bash

# MEP AI NABOX - Start Development Services
# This script starts all services including development UIs

set -e

echo "🚀 Starting MEP AI NABOX Development Services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env"
    # Use set -a to automatically export variables, and source the file
    set -a
    source .env
    set +a
else
    echo "⚠️  No .env file found. Using default values."
fi

# Start all services including development profiles
echo "🔧 Starting core services..."
docker compose up -d

echo "🖥️  Starting development services (UIs)..."
docker compose --profile dev up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
./scripts/health-check.sh

echo ""
echo "✅ Development services started successfully!"
echo ""
echo "🌐 Access URLs:"
echo "   PostgreSQL: localhost:5432"
echo "   Elasticsearch: http://localhost:9200"
echo "   Qdrant API: http://localhost:6333"
echo "   Neo4j: http://localhost:7474"
echo "   Redis: localhost:6379"
echo "   MinIO: http://localhost:9000"
echo ""
echo "🖥️  Development UIs:"
echo "   pgAdmin: http://localhost:8080 (admin@mep.local / admin_password)"
echo "   Elasticsearch Head: http://localhost:9100"
echo "   Neo4j Browser: http://localhost:7473"
echo "   Redis Commander: http://localhost:8081"
echo "   MinIO Console: http://localhost:9001"
echo "   Qdrant UI: http://localhost:7070"
echo ""
echo "📊 Monitoring:"
echo "   To start monitoring services: docker compose --profile monitoring up -d"
echo ""
echo "🛑 To stop all services: ./scripts/stop-services.sh" 