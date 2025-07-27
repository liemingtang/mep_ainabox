#!/bin/bash

# Database migration script for adding data source tracking fields
# This script adds new columns to track original file paths and data source information

set -e

echo "🔄 Starting database migration for data source tracking fields..."

# Check if we're in the right directory
if [ ! -f "app/database/migration_add_data_source_fields.sql" ]; then
    echo "❌ Migration file not found. Please run this script from the core_processor directory."
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Please start the database first."
    echo "   You can start it with: docker compose up -d postgres"
    exit 1
fi

# Set database connection parameters
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-mep_ainabox}
DB_USER=${POSTGRES_USER:-mep_user}
DB_PASSWORD=${POSTGRES_PASSWORD:-mep_password}

echo "📊 Database connection parameters:"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"

# Run the migration
echo "🚀 Running migration..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f app/database/migration_add_data_source_fields.sql

echo "✅ Migration completed successfully!"
echo ""
echo "📋 Migration summary:"
echo "   - Added original_file_path column"
echo "   - Added data_source_type column"
echo "   - Added data_source_uri column"
echo "   - Created indexes for better performance"
echo "   - Updated existing documents with default values"
echo ""
echo "🎉 Your database now supports tracking original file paths and data source information!" 