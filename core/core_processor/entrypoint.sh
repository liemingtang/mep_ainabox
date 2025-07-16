#!/bin/bash

# Entrypoint script for Core Processor
set -e

echo "Starting Core Processor initialization..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "PostgreSQL is ready!"

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -f http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cluster/health; do
    echo "Elasticsearch is unavailable - sleeping"
    sleep 5
done
echo "Elasticsearch is ready!"

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to be ready..."
until curl -f -H "api-key: $QDRANT_API_KEY" http://$QDRANT_HOST:$QDRANT_PORT/collections; do
    echo "Qdrant is unavailable - sleeping"
    sleep 2
done
echo "Qdrant is ready!"

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
until curl -f http://$NEO4J_HOST:7474/browser/; do
    echo "Neo4j is unavailable - sleeping"
    sleep 2
done
echo "Neo4j is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done
echo "Redis is ready!"

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until curl -f http://$MINIO_HOST:$MINIO_PORT/minio/health/live; do
    echo "MinIO is unavailable - sleeping"
    sleep 2
done
echo "MinIO is ready!"

# Initialize database schema
echo "Initializing database schema..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f /app/app/database/schema.sql

# Create necessary directories
mkdir -p /app/logs /app/documents /app/processed /app/temp

# Set correct permissions
chmod -R 755 /app/logs /app/documents /app/processed /app/temp

echo "Core Processor initialization completed!"

# Start the application
echo "Starting Core Processor application..."
exec python /app/main.py 