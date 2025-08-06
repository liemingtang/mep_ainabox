#!/bin/bash
#
# Queue Processing Worker Script - Docker-based
# Processes files from file_processing_queue table using text_processor.py
# Usage: ./process_file_processing_queue.sh [options]
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker image name
IMAGE_NAME="mep-folder-scanner:latest"
CONTAINER_NAME="mep-queue-worker-$(date +%s)"

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
            echo "  --processor-type <type>   Only process items with this processor type"
            echo "  --limit <number>          Maximum items to process per batch (default: 10)"
            echo "  --continuous              Run continuously"
            echo "  --interval <seconds>      Interval between batches in seconds (default: 30)"
            echo "  --dry-run                 Show what would be processed without making changes"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --processor-type text_processor"
            echo "  $0 --limit 5 --continuous"
            echo "  $0 --dry-run --processor-type default"
            echo "  $0 --continuous --interval 60"
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

# Use the batch processor for proper folder mounting
echo -e "${BLUE}🔍 Querying database for items to process...${NC}"

# Run the batch processor which handles folder mounting properly
cd "$SCRIPT_DIR"
python3 batch_process_file_queue.py "${ARGS[@]}"

# Display information
echo -e "${BLUE}🔧 Queue Processing Worker${NC}"
echo "=================================================="
echo -e "${YELLOW}Using batch processor for proper folder mounting${NC}"
echo -e "${YELLOW}Config directory:${NC} $CONFIG_PATH"

# Show arguments if any
if [[ ${#ARGS[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Arguments:${NC} ${ARGS[*]}"
fi

echo "=================================================="
echo ""

# Execute the batch processor
echo -e "${GREEN}🚀 Starting batch processor...${NC}"
echo "" 