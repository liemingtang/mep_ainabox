#!/bin/bash

# Entrypoint script for Core Processor
set -e

echo "Starting Core Processor initialization..."

# Wait for PostgreSQL to be ready (required)
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "PostgreSQL is ready!"

# Initialize database schema (required)
echo "Initializing database schema..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f /app/app/database/schema.sql

# Create necessary directories
mkdir -p /app/logs /app/documents /app/processed /app/temp

# Set correct permissions
chmod -R 755 /app/logs /app/documents /app/processed /app/temp

# Wait for other services with shorter timeouts (optional)
echo "Checking other services (optional)..."

# Wait for Elasticsearch to be ready (with timeout)
echo "Checking Elasticsearch..."
timeout 30 bash -c 'until curl -f http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cluster/health; do echo "Elasticsearch is unavailable - sleeping"; sleep 5; done' && echo "Elasticsearch is ready!" || echo "Elasticsearch not ready, continuing..."

# Wait for Qdrant to be ready (with timeout)
echo "Checking Qdrant..."
timeout 30 bash -c 'until curl -f -H "api-key: $QDRANT_API_KEY" http://$QDRANT_HOST:$QDRANT_PORT/collections; do echo "Qdrant is unavailable - sleeping"; sleep 2; done' && echo "Qdrant is ready!" || echo "Qdrant not ready, continuing..."

# Wait for Neo4j to be ready (with timeout)
echo "Checking Neo4j..."
timeout 30 bash -c 'until curl -f http://$NEO4J_HOST:7474/browser/; do echo "Neo4j is unavailable - sleeping"; sleep 2; done' && echo "Neo4j is ready!" || echo "Neo4j not ready, continuing..."

# Wait for Redis to be ready (with timeout)
echo "Checking Redis..."
timeout 30 bash -c 'until redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping; do echo "Redis is unavailable - sleeping"; sleep 2; done' && echo "Redis is ready!" || echo "Redis not ready, continuing..."

# Wait for MinIO to be ready (with timeout)
echo "Checking MinIO..."
timeout 30 bash -c 'until curl -f http://$MINIO_HOST:$MINIO_PORT/minio/health/live; do echo "MinIO is unavailable - sleeping"; sleep 2; done' && echo "MinIO is ready!" || echo "MinIO not ready, continuing..."

echo "Core Processor initialization completed!"

# Start the application
echo "Starting Core Processor application..."
exec python /app/main.py 