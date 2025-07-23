#!/bin/bash

# Dynamic Folder Scanner Script
# This script creates a temporary Docker container that mounts any folder on-the-fly
# and runs the folder scanner against it

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DRY_RUN=false
RECURSIVE=true
MAX_DEPTH=""
CONCURRENT=5
SAVE_REPORT=""
PROCESSOR_URL="http://localhost:8001"
CONTAINER_NAME="mep-folder-scanner-$(date +%s)"

# Function to show usage
show_usage() {
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "This script dynamically mounts any folder and scans it using a temporary Docker container."
    echo ""
    echo "Options:"
    echo "  --dry-run, -d          Show what would be processed without actually processing"
    echo "  --no-recursive         Disable recursive scanning (default: recursive)"
    echo "  --max-depth <depth>    Maximum depth for recursive scanning"
    echo "  --concurrent <num>     Number of concurrent processing tasks (default: 5)"
    echo "  --save-report <file>   Save processing report to specific file"
    echo "  --processor-url <url>  Core processor URL (default: http://localhost:8001)"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder"
    echo "  $0 /media/user/external_drive/documents --dry-run"
    echo "  $0 /home/user/documents --max-depth 3"
    echo "  $0 /mnt/network_share/files --no-recursive"
    echo "  $0 /path/to/folder --concurrent 10 --save-report my_report.json"
    echo ""
    echo "Note: The folder will be mounted read-only in the container for security."
}

# Parse command line arguments
FOLDER_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        --no-recursive)
            RECURSIVE=false
            shift
            ;;
        --max-depth)
            MAX_DEPTH="$2"
            shift 2
            ;;
        --concurrent)
            CONCURRENT="$2"
            shift 2
            ;;
        --save-report)
            SAVE_REPORT="$2"
            shift 2
            ;;
        --processor-url)
            PROCESSOR_URL="$2"
            shift 2
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$FOLDER_PATH" ]]; then
                FOLDER_PATH="$1"
            else
                echo "Multiple folder paths specified. Only one is allowed."
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if folder path is provided
if [[ -z "$FOLDER_PATH" ]]; then
    echo "Error: Folder path is required"
    show_usage
    exit 1
fi

# Check if folder exists
if [[ ! -d "$FOLDER_PATH" ]]; then
    echo "Error: Folder does not exist: $FOLDER_PATH"
    exit 1
fi

# Resolve absolute path
FOLDER_PATH="$(cd "$FOLDER_PATH" && pwd)"
echo "📁 Scanning folder: $FOLDER_PATH"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build the Docker run command
DOCKER_CMD="docker run --rm --name $CONTAINER_NAME"

# Add network if we need to connect to other services
if [[ "$PROCESSOR_URL" == *"localhost"* ]]; then
    # Use host network for localhost access
    DOCKER_CMD="$DOCKER_CMD --network host"
else
    # Use bridge network and set processor URL
    DOCKER_CMD="$DOCKER_CMD --network mep-ainabox_default"
fi

# Add volume mount for the folder
DOCKER_CMD="$DOCKER_CMD -v \"$FOLDER_PATH:/app/scan_folder:ro\""

# Add environment variables
DOCKER_CMD="$DOCKER_CMD -e CORE_PROCESSOR_URL=$PROCESSOR_URL"

# Add the image and command
DOCKER_CMD="$DOCKER_CMD mep-file-watcher:latest"

# Build the Python command
PYTHON_CMD="python3 /app/folder_scanner.py /app/scan_folder"

if [[ "$DRY_RUN" == true ]]; then
    PYTHON_CMD="$PYTHON_CMD --dry-run"
fi

if [[ "$RECURSIVE" == false ]]; then
    PYTHON_CMD="$PYTHON_CMD --no-recursive"
fi

if [[ -n "$MAX_DEPTH" ]]; then
    PYTHON_CMD="$PYTHON_CMD --max-depth $MAX_DEPTH"
fi

if [[ -n "$CONCURRENT" ]]; then
    PYTHON_CMD="$PYTHON_CMD --concurrent $CONCURRENT"
fi

if [[ -n "$SAVE_REPORT" ]]; then
    PYTHON_CMD="$PYTHON_CMD --save-report /app/scan_folder/$SAVE_REPORT"
fi

# Complete Docker command
FULL_CMD="$DOCKER_CMD $PYTHON_CMD"

echo "🚀 Starting dynamic folder scanner..."
echo "📋 Command: $FULL_CMD"
echo ""

# Execute the command
eval $FULL_CMD

echo ""
echo "✅ Dynamic folder scanning completed!"
echo "📁 Scanned folder: $FOLDER_PATH" 