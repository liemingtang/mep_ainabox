#!/bin/bash

# Quick HuggingFace Embeddings Health Check
# Simple one-liner health check

echo "🧠 Quick HuggingFace Health Check..."

# Check if container is running
if docker ps --filter "name=mep-huggingface-embeddings" --format "{{.Names}}" | grep -q "mep-huggingface-embeddings"; then
    echo "✅ Container is running"
    
    # Check if service is responding
    if curl -f -s http://localhost:8082/ > /dev/null 2>&1; then
        echo "✅ Service is responding"
        echo "✅ HuggingFace Embeddings is HEALTHY"
        exit 0
    else
        echo "❌ Service is not responding"
        echo "❌ HuggingFace Embeddings is UNHEALTHY"
        exit 1
    fi
else
    echo "❌ Container is not running"
    echo "❌ HuggingFace Embeddings is NOT RUNNING"
    exit 1
fi
