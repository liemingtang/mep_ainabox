#!/bin/bash
"""
Folder Scanner - Docker-based batch folder scanner
Usage: ./scan_folder.sh <folder_path> [options]
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker image name
IMAGE_NAME="mep-batch-processor:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MAX_DEPTH=""
SESSION_ID=""
DRY_RUN=""
FORCE=""
FOLDER_PATH=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-depth)
            MAX_DEPTH="$2"
            shift 2
            ;;
        --session-id)
            SESSION_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --force)
            FORCE="--force"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <folder_path> [options]"
            echo ""
            echo "Options:"
            echo "  --max-depth <number>    Maximum directory depth to scan"
            echo "  --session-id <id>       Custom session ID"
            echo "  --dry-run              Show what would be done without making changes"
            echo "  --force                Force scan all files regardless of changes"
            echo "  --help, -h             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 /home/user/documents"
            echo "  $0 /home/user/projects --max-depth 3"
            echo "  $0 /home/user/documents --dry-run"
            echo "  $0 /home/user/documents --force"
            echo ""
            echo "Docker Image: ${IMAGE_NAME}"
            exit 0
            ;;
        *)
            if [[ -z "$FOLDER_PATH" ]]; then
                FOLDER_PATH="$1"
            else
                echo -e "${RED}Error: Unknown option $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if folder path is provided
if [[ -z "$FOLDER_PATH" ]]; then
    echo -e "${RED}Error: Folder path is required${NC}"
    echo "Usage: $0 <folder_path> [options]"
    echo "Use --help for more information"
    exit 1
fi

# Check if folder exists
if [[ ! -d "$FOLDER_PATH" ]]; then
    echo -e "${RED}Error: Folder does not exist: $FOLDER_PATH${NC}"
    exit 1
fi

# Check if Docker image exists
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker image not found. Building it now...${NC}"
    if ! "$SCRIPT_DIR/build_docker.sh"; then
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
fi

# Get absolute paths
FOLDER_PATH=$(realpath "$FOLDER_PATH")
CONFIG_PATH="$PROJECT_ROOT/core/config"

# Check if config directory exists
if [[ ! -d "$CONFIG_PATH" ]]; then
    echo -e "${RED}Error: Config directory not found: $CONFIG_PATH${NC}"
    exit 1
fi

# Build Docker command
DOCKER_CMD="docker run --rm --network host"

# Mount the folder to scan
DOCKER_CMD="$DOCKER_CMD -v \"$FOLDER_PATH:/scan\""

# Pass host folder path as environment variable
DOCKER_CMD="$DOCKER_CMD -e HOST_FOLDER_PATH=\"$FOLDER_PATH\""

# Mount the config directory
DOCKER_CMD="$DOCKER_CMD -v \"$CONFIG_PATH:/app/config\""

# Override the entrypoint to run the folder scanner script
DOCKER_CMD="$DOCKER_CMD --entrypoint python3"

# Add the image name
DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME"

# Add the folder scanner script and scan path
DOCKER_CMD="$DOCKER_CMD /app/folder_scanner.py /scan"

# Add optional arguments
if [[ -n "$MAX_DEPTH" ]]; then
    DOCKER_CMD="$DOCKER_CMD --max-depth $MAX_DEPTH"
fi

if [[ -n "$SESSION_ID" ]]; then
    DOCKER_CMD="$DOCKER_CMD --session-id \"$SESSION_ID\""
fi

if [[ -n "$DRY_RUN" ]]; then
    DOCKER_CMD="$DOCKER_CMD $DRY_RUN"
fi

if [[ -n "$FORCE" ]]; then
    DOCKER_CMD="$DOCKER_CMD $FORCE"
fi

# Display information
echo -e "${BLUE}🔍 Folder Scanner${NC}"
echo "=================================================="
echo -e "${YELLOW}Folder to scan:${NC} $FOLDER_PATH"
echo -e "${YELLOW}Config directory:${NC} $CONFIG_PATH"
echo -e "${YELLOW}Docker image:${NC} $IMAGE_NAME"

if [[ -n "$MAX_DEPTH" ]]; then
    echo -e "${YELLOW}Max depth:${NC} $MAX_DEPTH"
fi

if [[ -n "$SESSION_ID" ]]; then
    echo -e "${YELLOW}Session ID:${NC} $SESSION_ID"
fi

if [[ -n "$DRY_RUN" ]]; then
    echo -e "${YELLOW}Mode:${NC} Dry run"
fi

if [[ -n "$FORCE" ]]; then
    echo -e "${YELLOW}Mode:${NC} Force scan"
fi

echo "=================================================="
echo ""

# Execute the Docker command
echo -e "${GREEN}🚀 Starting Docker container...${NC}"
echo ""

eval $DOCKER_CMD 