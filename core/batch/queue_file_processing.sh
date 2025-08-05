#!/bin/bash
"""
Queue File Processing Script - Docker-based
Adds files from file_info table to file_processing_queue table
Usage: ./queue_file_processing.sh [options]
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker image name
IMAGE_NAME="mep-folder-scanner:latest"
CONTAINER_NAME="mep-queue-processor-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --file-type <type>        Filter by file type (e.g., '.pdf', '.txt')"
            echo "  --mime-type <type>        Filter by MIME type (e.g., 'application/pdf')"
            echo "  --min-size <bytes>        Minimum file size in bytes"
            echo "  --max-size <bytes>        Maximum file size in bytes"
            echo "  --files-only              Only process files (exclude directories)"
            echo "  --directories-only        Only process directories"
            echo "  --priority <1-10>         Priority for queued items (default: 5)"
            echo "  --processor-type <type>   Processor type for the queue (default: default)"
            echo "  --limit <number>          Maximum number of files to queue"
            echo "  --dry-run                 Show what would be done without making changes"
            echo "  --stats                   Show queue statistics"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --file-type .pdf --priority 8"
            echo "  $0 --mime-type application/pdf --files-only"
            echo "  $0 --min-size 1000000 --max-size 10000000"
            echo "  $0 --stats"
            echo "  $0 --dry-run --limit 10"
            echo ""
            echo "Docker Image: ${IMAGE_NAME}"
            exit 0
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if Docker image exists
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker image not found. Building it now...${NC}"
    if ! "$SCRIPT_DIR/build_docker.sh"; then
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
fi

# Get absolute paths
CONFIG_PATH="$PROJECT_ROOT/core/config"

# Check if config directory exists
if [[ ! -d "$CONFIG_PATH" ]]; then
    echo -e "${RED}Error: Config directory not found: $CONFIG_PATH${NC}"
    exit 1
fi

# Build Docker command
DOCKER_CMD="docker run --rm --name $CONTAINER_NAME --network host"

# Mount the config directory
DOCKER_CMD="$DOCKER_CMD -v \"$CONFIG_PATH:/app/config\""

# Override the entrypoint to run the queue processing script
DOCKER_CMD="$DOCKER_CMD --entrypoint python3"

# Add the image name
DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME"

# Add the script and arguments
DOCKER_CMD="$DOCKER_CMD /app/queue_file_processing.py"

if [[ ${#ARGS[@]} -gt 0 ]]; then
    DOCKER_CMD="$DOCKER_CMD ${ARGS[*]}"
fi

# Display information
echo -e "${BLUE}🔧 Queue File Processing${NC}"
echo "=================================================="
echo -e "${YELLOW}Docker image:${NC} $IMAGE_NAME"
echo -e "${YELLOW}Config directory:${NC} $CONFIG_PATH"
echo -e "${YELLOW}Container name:${NC} $CONTAINER_NAME"

# Show arguments if any
if [[ ${#ARGS[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Arguments:${NC} ${ARGS[*]}"
fi

echo "=================================================="
echo ""

# Execute the Docker command
echo -e "${GREEN}🚀 Starting Docker container...${NC}"
echo ""

eval $DOCKER_CMD 