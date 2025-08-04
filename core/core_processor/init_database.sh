#!/bin/bash

# Database initialization script for MEP AINABOX
# This script creates the database and all necessary tables

set -e

echo "🔄 Starting database initialization for MEP AINABOX..."

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

# Create database if it doesn't exist
echo "🚀 Creating database if it doesn't exist..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database already exists or creation failed (this is OK)"

# Run the schema
echo "🚀 Running database schema..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f app/database/schema.sql

echo "✅ Database initialization completed successfully!"
echo ""
echo "📋 Database summary:"
echo "   - Created all necessary tables"
echo "   - Set up indexes for performance"
echo "   - Created views for data access"
echo "   - Set up triggers for data integrity"
echo ""
echo "🎉 Your database is now ready for use!" 