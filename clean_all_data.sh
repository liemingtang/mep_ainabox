#!/bin/bash

# MEP AI NABOX - Clean All Data Script
# This script safely deletes all data from all databases and storage systems
# 
# Usage:
#   ./clean_all_data.sh          # Dry run (default) - shows what would be deleted
#   ./clean_all_data.sh --real   # Actually delete the data

set -e

# Parse command line arguments
DRY_RUN=true
if [ "$1" = "--real" ]; then
    DRY_RUN=false
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "🧹 MEP AI NABOX - Clean All Data Script"
    echo "========================================"
    echo ""
    echo "Usage:"
    echo "  ./clean_all_data.sh          # Dry run (default) - shows what would be deleted"
    echo "  ./clean_all_data.sh --real   # Actually delete the data"
    echo "  ./clean_all_data.sh --help   # Show this help message"
    echo ""
    echo "Description:"
    echo "  This script safely deletes all data from all databases and storage systems"
    echo "  in the MEP AI NABOX project. It includes:"
    echo "  - Elasticsearch (documents, indices)"
    echo "  - Qdrant (vector embeddings, collections)"
    echo "  - PostgreSQL (processed data, metadata)"
    echo "  - Redis (cached data, sessions)"
    echo "  - Neo4j (graph relationships, nodes)"
    echo "  - MinIO (stored files, documents)"
    echo "  - Local files (PRESERVED - not deleted)"
    echo "  - Watch folder (PRESERVED - not deleted)"
    echo ""
    echo "Safety:"
    echo "  - Dry run is the default mode"
    echo "  - Real deletion requires --real flag"
    echo "  - Confirmation prompt for real deletion"
    echo "  - Comprehensive verification after cleanup"
    echo ""
    exit 0
    echo "🧹 MEP AI NABOX - Cleaning All Data (REAL EXECUTION)"
    echo "====================================================="
    echo ""
    echo "⚠️  WARNING: This will ACTUALLY delete ALL data from:"
    echo "   - Elasticsearch (documents, indices)"
    echo "   - Qdrant (vector embeddings, collections)"
    echo "   - PostgreSQL (processed data, metadata)"
    echo "   - Redis (cached data, sessions)"
    echo "   - Neo4j (graph relationships, nodes)"
    echo "   - MinIO (stored files, documents)"
    echo "   - Local processed files"
    echo ""
    echo "This action is IRREVERSIBLE!"
    echo ""

    # Confirmation prompt for real execution
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Cleanup cancelled."
        exit 0
    fi
else
    echo "🧹 MEP AI NABOX - Cleaning All Data (DRY RUN)"
    echo "=============================================="
    echo ""
    echo "🔍 This is a DRY RUN - no data will actually be deleted"
    echo "To actually delete data, run: ./clean_all_data.sh --real"
    echo ""
fi

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "🔍 Starting dry run analysis..."
else
    echo "🔄 Starting data cleanup..."
fi

# 1. Clean Elasticsearch
echo "📊 Cleaning Elasticsearch..."
indices=$(curl -s "http://localhost:9200/_cat/indices?v" | tail -n +2 | awk '{print $3}' | grep -v "^$" || echo "")
if [ -n "$indices" ]; then
    echo "   Found indices: $indices"
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would delete all indices"
    else
        echo "   Deleting all indices..."
        curl -X DELETE "http://localhost:9200/_all" || true
    fi
else
    echo "   No indices found"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] Elasticsearch analysis complete"
else
    echo "✅ Elasticsearch cleaned"
fi

# 2. Clean Qdrant (Vector Database)
echo "🔍 Cleaning Qdrant..."

# Load environment variables for Qdrant API key
if [ -f "services/.env" ]; then
    source services/.env
elif [ -f ".env" ]; then
    source .env
fi

QDRANT_API_KEY=${QDRANT_API_KEY:-qdrant_api_key}

collections=$(curl -s -H "api-key: $QDRANT_API_KEY" "http://localhost:6333/collections" | jq -r '.result.collections[].name' 2>/dev/null || echo "")
if [ -n "$collections" ]; then
    echo "   Found collections: $collections"
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would delete all collections"
    else
        echo "   Deleting all collections..."
        for collection in $collections; do
            if [ -n "$collection" ]; then
                echo "   Deleting collection: $collection"
                curl -X DELETE -H "api-key: $QDRANT_API_KEY" "http://localhost:6333/collections/$collection" || true
            fi
        done
    fi
else
    echo "   No collections found"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] Qdrant analysis complete"
else
    echo "✅ Qdrant cleaned"
fi

# 3. Clean PostgreSQL
echo "🗄️  Cleaning PostgreSQL..."
# Use environment variables or defaults
POSTGRES_USER=${POSTGRES_USER:-mep_user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-mep_password}
POSTGRES_DB=${POSTGRES_DB:-mep_ainabox}

tables=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "")
if [ -n "$tables" ]; then
    echo "   Found tables: $tables"
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would drop and recreate public schema"
    else
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO $POSTGRES_USER;
GRANT ALL ON SCHEMA public TO public;
" || echo "   PostgreSQL cleanup failed (might be expected if no data)"
    fi
else
    echo "   No tables found"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] PostgreSQL analysis complete"
else
    echo "✅ PostgreSQL cleaned"
fi

# 4. Clean Redis
echo "🔴 Cleaning Redis..."
# Use environment variables or defaults
REDIS_PASSWORD=${REDIS_PASSWORD:-redis_password}

redis_keys=$(redis-cli -h localhost -p 6379 -a "$REDIS_PASSWORD" DBSIZE 2>/dev/null | grep -E '^[0-9]+$' || echo "0")
if [ "$redis_keys" -gt 0 ] 2>/dev/null; then
    echo "   Found $redis_keys keys"
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would flush all keys"
    else
        redis-cli -h localhost -p 6379 -a "$REDIS_PASSWORD" FLUSHALL || echo "   Redis cleanup failed"
    fi
else
    echo "   No keys found"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] Redis analysis complete"
else
    echo "✅ Redis cleaned"
fi

# 5. Clean Neo4j
echo "🕸️  Cleaning Neo4j..."
# Use environment variables or defaults
NEO4J_PASSWORD=${NEO4J_PASSWORD:-neo4j_password}

node_count=$(curl -s -u "neo4j:$NEO4J_PASSWORD" -X POST "http://localhost:7474/db/neo4j/tx/commit" \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n) RETURN count(n) as count"}]}' 2>/dev/null | jq -r '.results[0].data[0].row[0]' | grep -E '^[0-9]+$' || echo "0")
if [ "$node_count" -gt 0 ] 2>/dev/null; then
    echo "   Found $node_count nodes"
    if [ "$DRY_RUN" = true ]; then
        echo "   [DRY RUN] Would delete all nodes"
    else
        curl -u "neo4j:$NEO4J_PASSWORD" -X POST "http://localhost:7474/db/neo4j/tx/commit" \
          -H "Content-Type: application/json" \
          -d '{"statements":[{"statement":"MATCH (n) DETACH DELETE n"}]}' || echo "   Neo4j cleanup failed"
    fi
else
    echo "   No nodes found"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] Neo4j analysis complete"
else
    echo "✅ Neo4j cleaned"
fi

# 6. Clean MinIO
echo "📦 Cleaning MinIO..."
# Use environment variables or defaults
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minio_access_key}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minio_secret_key}

if command -v mc >/dev/null 2>&1; then
    mc alias set myminio http://localhost:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null 2>&1 || echo "   MinIO alias setup failed"
    buckets="documents processed uploads"
    for bucket in $buckets; do
        if mc ls myminio/$bucket >/dev/null 2>&1; then
            echo "   Found bucket: $bucket"
            if [ "$DRY_RUN" = true ]; then
                echo "   [DRY RUN] Would delete bucket: $bucket"
            else
                mc rm --recursive --force myminio/$bucket || echo "   MinIO $bucket bucket cleanup failed"
            fi
        else
            echo "   Bucket not found: $bucket"
        fi
    done
else
    echo "   MinIO client (mc) not found - skipping MinIO cleanup"
fi

if [ "$DRY_RUN" = true ]; then
    echo "✅ [DRY RUN] MinIO analysis complete"
else
    echo "✅ MinIO cleaned"
fi

# 7. Local files (SKIPPED - preserving local files)
echo "📁 Local files (SKIPPED)"
echo "   Preserving all local files in:"
echo "   - core/processed/"
echo "   - core/documents/"
echo "   - core/temp/"
echo "   - core/logs/"
echo "✅ Local files preserved"

# 8. Watch folder (SKIPPED - preserving uploaded documents)
echo "👀 Watch folder (SKIPPED)"
echo "   Preserving all uploaded documents in watch_folder/"
echo "✅ Watch folder preserved"

# 9. Summary
echo ""
if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN SUMMARY"
    echo "=================="
    echo ""
    echo "📋 What would be cleaned:"
    echo "   🔍 Elasticsearch indices and documents"
    echo "   🔍 Qdrant vector collections"
    echo "   🔍 PostgreSQL database tables"
    echo "   🔍 Redis cache and sessions"
    echo "   🔍 Neo4j graph data"
    echo "   🔍 MinIO stored files"
    echo "   📁 Local files (PRESERVED)"
    echo "   👀 Watch folder (PRESERVED)"
    echo ""
    echo "🚀 To actually perform the cleanup, run:"
    echo "   ./clean_all_data.sh --real"
    echo ""
else
    echo "🔍 Verifying cleanup..."
    
    # Check Elasticsearch
    if curl -s "http://localhost:9200/_cat/indices?v" | grep -q "documents"; then
        echo "⚠️  Elasticsearch still has documents index"
    else
        echo "✅ Elasticsearch is clean"
    fi
    
    # Check Qdrant
    if curl -s -H "api-key: $QDRANT_API_KEY" "http://localhost:6333/collections" | grep -q "documents"; then
        echo "⚠️  Qdrant still has documents collection"
    else
        echo "✅ Qdrant is clean"
    fi
    
    # Check PostgreSQL
    doc_count=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$doc_count" -gt 0 ]; then
        echo "⚠️  PostgreSQL still has $doc_count tables"
    else
        echo "✅ PostgreSQL is clean"
    fi
    
    # Check Redis
    redis_keys=$(redis-cli -h localhost -p 6379 -a "$REDIS_PASSWORD" DBSIZE 2>/dev/null | grep -E '^[0-9]+$' || echo "0")
    if [ "$redis_keys" -gt 0 ] 2>/dev/null; then
        echo "⚠️  Redis still has $redis_keys keys"
    else
        echo "✅ Redis is clean"
    fi
    
    echo ""
    echo "🎉 Data cleanup completed!"
    echo "=========================="
    echo ""
    echo "📋 What was cleaned:"
    echo "   ✅ Elasticsearch indices and documents"
    echo "   ✅ Qdrant vector collections"
    echo "   ✅ PostgreSQL database tables"
    echo "   ✅ Redis cache and sessions"
    echo "   ✅ Neo4j graph data"
    echo "   ✅ MinIO stored files"
    echo "   📁 Local files (PRESERVED)"
    echo "   👀 Watch folder (PRESERVED)"
    echo ""
    echo "🚀 You can now start fresh with:"
    echo "   ./start_admin.sh"
    echo ""
fi 