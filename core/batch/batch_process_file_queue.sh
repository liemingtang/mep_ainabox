#!/bin/bash
#
# Batch Process File Queue Script
# Queries database and dynamically mounts folders for processing
# Usage: ./batch_process_file_queue.sh [options]
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker image name (unified scanner/worker image)
IMAGE_NAME="mep-folder-scanner:latest"
CONTAINER_NAME="mep-batch-processor-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
ARGS=()
SCRIPT_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --processor-type <type>   Only process items with this processor type"
            echo "  --limit <number>          Maximum items to process per batch (default: 10)"
            echo "  --dry-run                 Show what would be processed without making changes"
            echo "  --script-args <args>      Additional arguments to pass to the worker script"
            echo "  --help, -h                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --processor-type text_processor"
            echo "  $0 --limit 5 --dry-run"
            echo "  $0 --processor-type default --script-args --continuous"
            echo ""
            echo "Docker Image: ${IMAGE_NAME}"
            exit 0
            ;;
        --script-args)
            shift
            while [[ $# -gt 0 ]]; do
                if [[ $1 == --* ]]; then
                    break
                fi
                SCRIPT_ARGS+=("$1")
                shift
            done
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

# Add docker.sock group to allow non-root access to Docker inside container
if [[ -S "/var/run/docker.sock" ]]; then
  DOCKER_SOCK_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "")
  if [[ -n "$DOCKER_SOCK_GID" ]]; then
    DOCKER_CMD="$DOCKER_CMD --group-add $DOCKER_SOCK_GID"
  fi
fi

# Mount the entire core directory so container uses latest host code (/app mirrors core)
DOCKER_CMD="$DOCKER_CMD -v \"$PROJECT_ROOT/core:/app\""

# Mount the services directory for .env file access
DOCKER_CMD="$DOCKER_CMD -v \"$PROJECT_ROOT/services:/services:ro\""
echo -e "${YELLOW}📁 Mounting services directory: $PROJECT_ROOT/services -> /services${NC}"

# Pass host core path so orchestrator can mount config into the worker
DOCKER_CMD="$DOCKER_CMD -e DOCKER_HOST_CORE_PATH=\"$PROJECT_ROOT/core\""



# Mount Docker socket for Docker-in-Docker capability
DOCKER_CMD="$DOCKER_CMD -v /var/run/docker.sock:/var/run/docker.sock"

# Mount the external drive folder where files are located
# This is needed because the files are on an external drive
if [[ -d "/media/lie/DATA2/ai_scan_folder" ]]; then
    DOCKER_CMD="$DOCKER_CMD -v \"/media/lie/DATA2/ai_scan_folder:/mnt/ai_scan_folder:ro\""
    echo -e "${YELLOW}📁 Mounting external drive: /media/lie/DATA2/ai_scan_folder -> /mnt/ai_scan_folder${NC}"
fi

# Also mount the local test files directory if it exists
if [[ -d "$PROJECT_ROOT/core/test_files" ]]; then
    DOCKER_CMD="$DOCKER_CMD -v \"$PROJECT_ROOT/core/test_files:/mnt/test_files:ro\""
    echo -e "${YELLOW}📁 Mounting local test files: $PROJECT_ROOT/core/test_files -> /mnt/test_files${NC}"
fi

# Override the entrypoint to run the orchestrator script (python3 is image entrypoint by default, but set explicitly)
DOCKER_CMD="$DOCKER_CMD --entrypoint python3"

# Add the image name
DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME"

# Run the orchestrator that dynamically mounts parent folders and spawns the worker
DOCKER_CMD="$DOCKER_CMD /app/batch/batch_process_file_queue.py"

if [[ ${#ARGS[@]} -gt 0 ]]; then
    DOCKER_CMD="$DOCKER_CMD ${ARGS[*]}"
fi

# Add script arguments if any
if [[ ${#SCRIPT_ARGS[@]} -gt 0 ]]; then
    DOCKER_CMD="$DOCKER_CMD --script-args ${SCRIPT_ARGS[*]}"
fi

# Display information
echo -e "${BLUE}🔧 Batch Process File Queue${NC}"
echo "=================================================="
echo -e "${YELLOW}Docker image:${NC} $IMAGE_NAME"
echo -e "${YELLOW}Config directory:${NC} $CONFIG_PATH"
echo -e "${YELLOW}Container name:${NC} $CONTAINER_NAME"

# Show arguments if any
if [[ ${#ARGS[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Arguments:${NC} ${ARGS[*]}"
fi

# Show script arguments if any
if [[ ${#SCRIPT_ARGS[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Script Arguments:${NC} ${SCRIPT_ARGS[*]}"
fi

echo "=================================================="
echo ""

# Execute the Docker command
echo -e "${GREEN}🚀 Starting Docker container...${NC}"
echo ""

echo "docker cmd: " $DOCKER_CMD

eval $DOCKER_CMD 