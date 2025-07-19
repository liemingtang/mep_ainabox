#!/bin/bash

# MEP AI NABOX - Stop Admin Script
# This script completely shuts down all services and cleans up all processes

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 MEP AI NABOX - Complete System Shutdown${NC}"
echo "=================================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Stop the dashboard (host-based)
print_status "Step 1: Stopping Dashboard Service..."
if pgrep -f "python.*dashboard.*main.py" > /dev/null; then
    print_status "Found dashboard process, stopping..."
    pkill -f "python.*dashboard.*main.py" || true
    sleep 2
    
    # Force kill if still running
    if pgrep -f "python.*dashboard.*main.py" > /dev/null; then
        print_warning "Dashboard still running, force killing..."
        pkill -9 -f "python.*dashboard.*main.py" || true
    fi
    print_success "Dashboard stopped"
else
    print_warning "No dashboard process found"
fi

# Step 2: Stop all Python main.py processes
print_status "Step 2: Stopping all Python main.py processes..."
PYTHON_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ -n "$PYTHON_PIDS" ]; then
    print_status "Found Python processes: $PYTHON_PIDS"
    echo "$PYTHON_PIDS" | xargs -r kill -TERM 2>/dev/null || true
    sleep 3
    
    # Force kill remaining processes
    REMAINING_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null || true)
    if [ -n "$REMAINING_PIDS" ]; then
        print_warning "Force killing remaining Python processes..."
        echo "$REMAINING_PIDS" | xargs -r kill -9 2>/dev/null || true
    fi
    print_success "All Python processes stopped"
else
    print_warning "No Python main.py processes found"
fi

# Step 3: Stop Core System Services
print_status "Step 3: Stopping Core System Services..."
if [ -d "core" ]; then
    cd core
    if command_exists docker; then
        print_status "Stopping core Docker services..."
        docker compose down --remove-orphans 2>/dev/null || true
        print_success "Core services stopped"
    else
        print_warning "Docker not found, skipping core services"
    fi
    cd ..
else
    print_warning "Core directory not found"
fi

# Step 4: Stop Infrastructure Services
print_status "Step 4: Stopping Infrastructure Services..."
if [ -d "services" ]; then
    cd services
    if command_exists docker; then
        print_status "Stopping infrastructure Docker services..."
        docker compose down --remove-orphans 2>/dev/null || true
        
        # Stop development services if they exist
        print_status "Stopping development services..."
        docker compose --profile dev down --remove-orphans 2>/dev/null || true
        
        # Stop monitoring services if they exist
        print_status "Stopping monitoring services..."
        docker compose --profile monitoring down --remove-orphans 2>/dev/null || true
        
        print_success "Infrastructure services stopped"
    else
        print_warning "Docker not found, skipping infrastructure services"
    fi
    cd ..
else
    print_warning "Services directory not found"
fi

# Step 5: Stop any remaining MEP containers
print_status "Step 5: Stopping any remaining MEP containers..."
if command_exists docker; then
    MEP_CONTAINERS=$(docker ps -q --filter "name=mep-" 2>/dev/null || true)
    if [ -n "$MEP_CONTAINERS" ]; then
        print_status "Found MEP containers: $MEP_CONTAINERS"
        echo "$MEP_CONTAINERS" | xargs -r docker stop 2>/dev/null || true
        echo "$MEP_CONTAINERS" | xargs -r docker rm 2>/dev/null || true
        print_success "Remaining MEP containers stopped and removed"
    else
        print_warning "No MEP containers found"
    fi
else
    print_warning "Docker not found, skipping container cleanup"
fi

# Step 6: Clean up any orphaned containers
print_status "Step 6: Cleaning up orphaned containers..."
if command_exists docker; then
    ORPHANED_CONTAINERS=$(docker ps -aq --filter "name=mep-" 2>/dev/null || true)
    if [ -n "$ORPHANED_CONTAINERS" ]; then
        print_status "Found orphaned MEP containers: $ORPHANED_CONTAINERS"
        echo "$ORPHANED_CONTAINERS" | xargs -r docker rm -f 2>/dev/null || true
        print_success "Orphaned containers cleaned up"
    else
        print_warning "No orphaned containers found"
    fi
else
    print_warning "Docker not found, skipping orphaned container cleanup"
fi

# Step 7: Stop Qdrant UI if running
print_status "Step 7: Stopping Qdrant UI..."
if pgrep -f "python.*qdrant.*server.py" > /dev/null; then
    print_status "Found Qdrant UI process, stopping..."
    pkill -f "python.*qdrant.*server.py" || true
    sleep 2
    
    # Force kill if still running
    if pgrep -f "python.*qdrant.*server.py" > /dev/null; then
        print_warning "Qdrant UI still running, force killing..."
        pkill -9 -f "python.*qdrant.*server.py" || true
    fi
    print_success "Qdrant UI stopped"
else
    print_warning "No Qdrant UI process found"
fi

# Step 8: Final cleanup - kill any remaining related processes
print_status "Step 8: Final cleanup..."
REMAINING_PROCESSES=$(pgrep -f "mep\|dashboard\|qdrant" 2>/dev/null || true)
if [ -n "$REMAINING_PROCESSES" ]; then
    print_warning "Found remaining related processes: $REMAINING_PROCESSES"
    echo "$REMAINING_PROCESSES" | xargs -r kill -TERM 2>/dev/null || true
    sleep 2
    echo "$REMAINING_PROCESSES" | xargs -r kill -9 2>/dev/null || true
    print_success "Remaining processes cleaned up"
else
    print_success "No remaining processes found"
fi

# Step 9: Verify shutdown
print_status "Step 9: Verifying shutdown..."
echo ""

# Check for remaining Python processes
PYTHON_REMAINING=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ -n "$PYTHON_REMAINING" ]; then
    print_error "Warning: Some Python processes still running: $PYTHON_REMAINING"
else
    print_success "All Python processes stopped"
fi

# Check for remaining MEP containers
if command_exists docker; then
    MEP_REMAINING=$(docker ps -q --filter "name=mep-" 2>/dev/null || true)
    if [ -n "$MEP_REMAINING" ]; then
        print_error "Warning: Some MEP containers still running: $MEP_REMAINING"
    else
        print_success "All MEP containers stopped"
    fi
else
    print_warning "Docker not available for verification"
fi

# Check for dashboard process
DASHBOARD_REMAINING=$(pgrep -f "python.*dashboard.*main.py" 2>/dev/null || true)
if [ -n "$DASHBOARD_REMAINING" ]; then
    print_error "Warning: Dashboard process still running: $DASHBOARD_REMAINING"
else
    print_success "Dashboard process stopped"
fi

echo ""
echo -e "${GREEN}🎉 MEP AI NABOX System Shutdown Complete!${NC}"
echo "=================================================="
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo "  • Dashboard service: Stopped"
echo "  • Core system services: Stopped"
echo "  • Infrastructure services: Stopped"
echo "  • Development services: Stopped"
echo "  • Monitoring services: Stopped"
echo "  • Python processes: Cleaned up"
echo "  • Docker containers: Cleaned up"
echo ""
echo -e "${YELLOW}💡 To restart the system:${NC}"
echo "  ./start_admin.sh"
echo ""
echo -e "${YELLOW}💡 To check if anything is still running:${NC}"
echo "  ps aux | grep -E '(mep|dashboard|qdrant)'"
echo "  docker ps | grep mep" 