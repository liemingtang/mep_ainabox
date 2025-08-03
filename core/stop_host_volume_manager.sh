#!/bin/bash

# Host Volume Manager Stop Script
# This script stops the host-side volume manager service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PID_FILE="host_volume_manager.pid"

echo -e "${BLUE}🛑 Stopping Host Volume Manager Service${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  No PID file found. Service may not be running.${NC}"
    exit 0
fi

# Read PID from file
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Process $PID is not running. Removing stale PID file.${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

# Stop the process
echo -e "${CYAN}🛑 Stopping process $PID...${NC}"
kill "$PID"

# Wait for process to stop
sleep 2

# Check if process stopped
if ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Process didn't stop gracefully. Force killing...${NC}"
    kill -9 "$PID"
    sleep 1
fi

# Remove PID file
rm -f "$PID_FILE"

echo -e "${GREEN}✅ Host Volume Manager stopped successfully${NC}" 