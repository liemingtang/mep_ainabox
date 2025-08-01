#!/bin/bash

# Dynamic Text Processor Script
# This script creates a temporary Docker container that mounts any folder on-the-fly
# and runs text extraction on files within that folder

set -e

# Default values
DRY_RUN=false
OUTPUT_FORMAT="json"
CONCURRENT=5
MAX_DEPTH=0
RECURSIVE=true
CONTAINER_NAME="mep-text-processor-dynamic-$(date +%s)"

# Function to show usage
show_usage() {
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "This script dynamically mounts any folder and runs text extraction on files within it."
    echo ""
    echo "Options:"
    echo "  --dry-run, -d          Show what would be processed without actually processing"
    echo "  --output <format>       Output format: json, text, or raw (default: json)"
    echo "  --concurrent <num>      Number of concurrent processing tasks (default: 5)"
    echo "  --max-depth <depth>     Maximum depth for recursive scanning (default: 0)"
    echo "  --no-recursive          Disable recursive scanning (default: recursive)"
    echo "  --help, -h              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder"
    echo "  $0 /media/user/external_drive/documents --dry-run"
    echo "  $0 /home/user/documents --max-depth 3"
    echo "  $0 /mnt/network_share/files --no-recursive"
    echo "  $0 /path/to/folder --concurrent 10 --output text"
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
        --output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --concurrent)
            CONCURRENT="$2"
            shift 2
            ;;
        --max-depth)
            MAX_DEPTH="$2"
            shift 2
            ;;
        --no-recursive)
            RECURSIVE=false
            shift
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
echo "📁 Processing folder: $FOLDER_PATH"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build the Docker run command
DOCKER_CMD="docker run --rm --name $CONTAINER_NAME"

# Use host network for localhost access to other services
DOCKER_CMD="$DOCKER_CMD --network host"

# Add volume mount for the folder
DOCKER_CMD="$DOCKER_CMD -v \"$FOLDER_PATH:/app/scan_folder:ro\""

# Add environment variables
DOCKER_CMD="$DOCKER_CMD -e CORE_PROCESSOR_URL=http://localhost:8001"
DOCKER_CMD="$DOCKER_CMD -e PROCESSING_PIPELINE_URL=http://localhost:8003"
DOCKER_CMD="$DOCKER_CMD -e HOST_SCAN_FOLDER_PATH=$FOLDER_PATH"

# Add the image and command
DOCKER_CMD="$DOCKER_CMD mep-text-processor:latest"

# Build the Python command
PYTHON_CMD="python3 /app/text_processor_dynamic.py /app/scan_folder"

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

if [[ -n "$OUTPUT_FORMAT" ]]; then
    PYTHON_CMD="$PYTHON_CMD --output $OUTPUT_FORMAT"
fi

# Complete Docker command
FULL_CMD="$DOCKER_CMD $PYTHON_CMD"

echo "🚀 Starting dynamic text processor..."
echo "📋 Command: $FULL_CMD"
echo ""

# Execute the command
eval $FULL_CMD

echo ""
echo "✅ Dynamic text processing completed!"
echo "📁 Processed folder: $FOLDER_PATH" 