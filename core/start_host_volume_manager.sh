#!/bin/bash

# Host Volume Manager Startup Script
# This script starts the host-side volume manager service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="host-volume-manager"
PORT=8011
PID_FILE="host_volume_manager.pid"
LOG_FILE="logs/host_volume_manager.log"

# Create logs directory if it doesn't exist
mkdir -p logs

echo -e "${BLUE}🚀 Starting Host Volume Manager Service${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if service is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Host Volume Manager is already running (PID: $PID)${NC}"
        echo "Use './stop_host_volume_manager.sh' to stop it first"
        exit 1
    else
        echo "Removing stale PID file..."
        rm -f "$PID_FILE"
    fi
fi

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Port $PORT is already in use${NC}"
    exit 1
fi

# Start the service
echo -e "${CYAN}📦 Starting host volume manager on port $PORT...${NC}"
python3 host_volume_manager.py serve --port $PORT > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

# Wait a moment for the service to start
sleep 2

# Check if service started successfully
if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Host Volume Manager started successfully (PID: $PID)${NC}"
    echo -e "${GREEN}🌐 Service URL: http://localhost:$PORT${NC}"
    echo -e "${GREEN}📋 API Endpoints:${NC}"
    echo -e "${CYAN}  Health Check:${NC} http://localhost:$PORT/health"
    echo -e "${CYAN}  Mount Folder:${NC} POST http://localhost:$PORT/mount"
    echo -e "${CYAN}  List Folders:${NC} GET http://localhost:$PORT/list"
    echo -e "${CYAN}  Unmount Folder:${NC} POST http://localhost:$PORT/unmount"
    echo -e "${CYAN}  Cleanup:${NC} POST http://localhost:$PORT/cleanup"
    echo ""
    echo -e "${YELLOW}💡 Logs:${NC} tail -f $LOG_FILE"
    echo -e "${YELLOW}🛑 Stop:${NC} ./stop_host_volume_manager.sh"
else
    echo -e "${RED}❌ Failed to start Host Volume Manager${NC}"
    echo "Check logs: tail -f $LOG_FILE"
    exit 1
fi 