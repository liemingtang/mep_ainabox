#!/bin/bash

# Dynamic File Watcher Script
# This script creates a temporary Docker container that mounts any folder on-the-fly
# and starts a file watcher to monitor it for new files

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
PROCESSOR_URL="http://localhost:8001"
CONTAINER_NAME="mep-dynamic-watcher-$(date +%s)"
WATCH_MODE="continuous"  # continuous or scan-once
SCAN_ONCE=false

# Function to show usage
show_usage() {
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "This script dynamically mounts any folder and starts a file watcher to monitor it."
    echo ""
    echo "Options:"
    echo "  --scan-once            Scan the folder once and exit (default: continuous watching)"
    echo "  --processor-url <url>  Core processor URL (default: http://localhost:8001)"
    echo "  --container-name <name> Custom container name (default: auto-generated)"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder                    # Watch folder continuously"
    echo "  $0 /media/user/external_drive/documents --scan-once"
    echo "  $0 /home/user/documents --processor-url http://192.168.1.100:8001"
    echo ""
    echo "Note: The folder will be mounted read-only in the container for security."
    echo "Press Ctrl+C to stop the file watcher."
}

# Parse command line arguments
FOLDER_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --scan-once)
            SCAN_ONCE=true
            WATCH_MODE="scan-once"
            shift
            ;;
        --processor-url)
            PROCESSOR_URL="$2"
            shift 2
            ;;
        --container-name)
            CONTAINER_NAME="$2"
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
echo "📁 Watching folder: $FOLDER_PATH"
echo "🔄 Mode: $WATCH_MODE"

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
DOCKER_CMD="$DOCKER_CMD -v \"$FOLDER_PATH:/app/watch_folder:ro\""

# Add environment variables
DOCKER_CMD="$DOCKER_CMD -e CORE_PROCESSOR_URL=$PROCESSOR_URL"
DOCKER_CMD="$DOCKER_CMD -e WATCH_PATHS=/app/watch_folder"

# Add the image
DOCKER_CMD="$DOCKER_CMD mep-file-watcher:latest"

if [[ "$SCAN_ONCE" == true ]]; then
    # For scan-once mode, run the folder scanner
    echo "🚀 Starting one-time folder scan..."
    PYTHON_CMD="python3 /app/folder_scanner.py /app/watch_folder"
    FULL_CMD="$DOCKER_CMD $PYTHON_CMD"
    
    echo "📋 Command: $FULL_CMD"
    echo ""
    
    # Execute the command
    eval $FULL_CMD
    
    echo ""
    echo "✅ One-time folder scan completed!"
    echo "📁 Scanned folder: $FOLDER_PATH"
else
    # For continuous mode, start the file watcher
    echo "🚀 Starting continuous file watcher..."
    echo "📋 Container name: $CONTAINER_NAME"
    echo "🌐 Processor URL: $PROCESSOR_URL"
    echo ""
    echo "The file watcher is now monitoring the folder for new files."
    echo "Press Ctrl+C to stop the watcher."
    echo ""
    
    # Start the file watcher in the background
    FULL_CMD="$DOCKER_CMD python3 /app/main.py"
    
    # Execute the command (this will run until interrupted)
    eval $FULL_CMD
fi 