#!/bin/bash
"""
Build and run the folder scanner Docker container
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker image name and tag
IMAGE_NAME="mep-folder-scanner"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Building MEP Folder Scanner Docker Image${NC}"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Build the Docker image
echo -e "${YELLOW}📦 Building Docker image: ${FULL_IMAGE_NAME}${NC}"
cd "$SCRIPT_DIR"

if docker build -t "$FULL_IMAGE_NAME" .; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Usage Examples:${NC}"
    echo "=================================================="
    echo ""
    echo -e "${YELLOW}Basic usage:${NC}"
    echo "docker run --rm -v /path/to/folder:/scan -v /path/to/config:/app/config ${FULL_IMAGE_NAME} /scan"
    echo ""
    echo -e "${YELLOW}With options:${NC}"
    echo "docker run --rm -v /path/to/folder:/scan -v /path/to/config:/app/config ${FULL_IMAGE_NAME} /scan --max-depth 3 --session-id my_scan"
    echo ""
    echo -e "${YELLOW}Dry run:${NC}"
    echo "docker run --rm -v /path/to/folder:/scan -v /path/to/config:/app/config ${FULL_IMAGE_NAME} /scan --dry-run"
    echo ""
    echo -e "${YELLOW}Help:${NC}"
    echo "docker run --rm ${FULL_IMAGE_NAME} --help"
    echo ""
    echo -e "${BLUE}📝 Note:${NC}"
    echo "- Mount your folder to /scan inside the container"
    echo "- Mount your config directory to /app/config for database connection"
    echo "- The container will use the PostgreSQL configuration from the mounted config"
    echo ""
    echo -e "${GREEN}🎉 Ready to use!${NC}"
else
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
fi 