#!/bin/bash

# MEP AI NABOX - Dashboard Docker Startup Script
# This script starts the dashboard service in Docker with local folder mounted

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 MEP AI NABOX - Dashboard Docker Startup${NC}"
echo -e "${BLUE}============================================${NC}"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found. Please run this script from the core directory.${NC}"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Error: docker compose is not available${NC}"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Error: Docker daemon is not running. Please start Docker first.${NC}"
    exit 1
fi

# Parse command line arguments
BACKGROUND=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --background)
            BACKGROUND=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --background     Start in background mode"
            echo "  --skip-build     Skip building Docker image"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "EXAMPLES:"
            echo "  $0               # Start dashboard in foreground"
            echo "  $0 --background  # Start dashboard in background"
            echo "  $0 --skip-build  # Use existing image"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Clean up existing dashboard processes
echo -e "${BLUE}🧹 Cleaning up existing dashboard processes...${NC}"

# Stop existing dashboard container
if docker ps -q -f name=mep-dashboard | grep -q .; then
    echo "Stopping existing dashboard container..."
    docker stop mep-dashboard || true
    docker rm mep-dashboard || true
fi

# Kill any existing dashboard processes on host
if pgrep -f "python3.*dashboard.*main.py" > /dev/null; then
    echo "Stopping existing dashboard process on host..."
    pkill -f "python3.*dashboard.*main.py" || true
    sleep 2
fi

# Clean up stale PID files
if [ -f "dashboard.pid" ]; then
    PID=$(cat dashboard.pid)
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Removing stale dashboard PID file..."
        rm -f dashboard.pid
    fi
fi

echo -e "${GREEN}✅ Cleanup completed${NC}"

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p dashboard/logs
mkdir -p logs
mkdir -p config

# Set proper permissions
echo -e "${BLUE}🔐 Setting proper permissions...${NC}"
chmod -R 755 dashboard/logs logs config 2>/dev/null || true

# Load environment variables
echo -e "${BLUE}📋 Loading environment variables...${NC}"
if [ -f ".env" ]; then
    echo "Loading environment variables..."
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "$line" ]]; then
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                export "$line"
            fi
        fi
    done < .env
else
    echo -e "${YELLOW}⚠️  .env file not found. Using default values.${NC}"
fi

# Build Docker image (if not skipped)
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${BLUE}🔨 Building dashboard Docker image...${NC}"
    docker compose build dashboard
    echo -e "${GREEN}✅ Dashboard image built successfully${NC}"
else
    echo -e "${YELLOW}⏭️  Skipping Docker build (--skip-build flag used)${NC}"
fi

# Start dashboard service
echo -e "${BLUE}🚀 Starting dashboard service...${NC}"

if [ "$BACKGROUND" = true ]; then
    echo "Starting dashboard in background mode..."
    docker compose up -d dashboard
    
    # Wait for dashboard to be ready
    echo -e "${BLUE}⏳ Waiting for dashboard to start...${NC}"
    sleep 15
    
    # Check if dashboard is healthy
    echo -e "${BLUE}🔍 Checking dashboard health...${NC}"
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Dashboard is ready!${NC}"
            break
        else
            echo -e "${YELLOW}⏳ Waiting for dashboard... (attempt $((attempt + 1))/$max_attempts)${NC}"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ Dashboard failed to start properly.${NC}"
        echo "Check logs with: docker compose logs dashboard"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Dashboard started successfully in background mode!${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo ""
    echo -e "${BLUE}🌐 Dashboard URL:${NC} http://localhost:8010"
    echo -e "${BLUE}🔧 Admin Panel:${NC} http://localhost:8010/admin"
    echo ""
    echo -e "${BLUE}📊 Useful Commands:${NC}"
    echo -e "${CYAN}  View logs:${NC} docker compose logs -f dashboard"
    echo -e "${CYAN}  Stop dashboard:${NC} docker compose stop dashboard"
    echo -e "${CYAN}  Restart dashboard:${NC} docker compose restart dashboard"
    echo -e "${CYAN}  View container status:${NC} docker ps -f name=mep-dashboard"
    echo ""
else
    echo "Starting dashboard in foreground mode..."
    echo -e "${GREEN}✅ Dashboard will be available at http://localhost:8010${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the dashboard${NC}"
    echo ""
    docker compose up dashboard
fi
