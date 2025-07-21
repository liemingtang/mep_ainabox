#!/bin/bash

# Dynamic Text Processor Script
# This script creates a temporary Docker container that mounts any folder on-the-fly
# and extracts text from files in it

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DRY_RUN=false
RECURSIVE=true
MAX_DEPTH=""
CONCURRENT=5
OUTPUT_FORMAT="json"
PROCESSING_PIPELINE_URL="http://localhost:8003"
CONTAINER_NAME="mep-text-processor-$(date +%s)"

# Function to show usage
show_usage() {
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "This script dynamically mounts any folder and extracts text from files using a temporary Docker container."
    echo ""
    echo "Options:"
    echo "  --dry-run, -d          Show what would be processed without actually doing it"
    echo "  --recursive, -r         Process subdirectories recursively (default: true)"
    echo "  --no-recursive          Don't process subdirectories"
    echo "  --max-depth <depth>     Maximum directory depth to scan"
    echo "  --concurrent <num>      Number of concurrent processing jobs (default: 5)"
    echo "  --output <format>       Output format: json, text, summary (default: json)"
    echo "  --pipeline-url <url>    Processing pipeline URL (default: http://localhost:8003)"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/documents --dry-run"
    echo "  $0 /path/to/documents --max-depth 2 --concurrent 10"
    echo "  $0 /path/to/documents --output summary"
}

# Parse command line arguments
FOLDER_PATH=""
REMAINING_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        --recursive|-r)
            RECURSIVE=true
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
        --output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --pipeline-url)
            PROCESSING_PIPELINE_URL="$2"
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
                REMAINING_ARGS+=("$1")
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
    echo "Error: Folder '$FOLDER_PATH' does not exist"
    exit 1
fi

# Get absolute path
FOLDER_PATH="$(cd "$FOLDER_PATH" && pwd)"

# Run the text processor in a Docker container
echo "Running text processor in Docker container for folder: $FOLDER_PATH" >&2

# Build the command string
CMD_STRING="cd /app/core/processors/text_processor && pip install -r /app/core/processors/text_processor/requirements.txt && python text_processor.py /app/input"

if [[ "$DRY_RUN" == "true" ]]; then
    CMD_STRING="$CMD_STRING --dry-run"
fi

if [[ "$RECURSIVE" == "false" ]]; then
    CMD_STRING="$CMD_STRING --no-recursive"
fi

if [[ -n "$MAX_DEPTH" ]]; then
    CMD_STRING="$CMD_STRING --max-depth $MAX_DEPTH"
fi

CMD_STRING="$CMD_STRING --concurrent $CONCURRENT --output $OUTPUT_FORMAT"

# Build the Docker command
DOCKER_CMD=(
    docker run --rm
    -v "$FOLDER_PATH:/app/input"
    -v "$SCRIPT_DIR:/app/core"
    -w /app
    --name "$CONTAINER_NAME"
    python:3.9-slim
    bash -c "$CMD_STRING 2>/dev/null"
)

# Execute the Docker command and capture only the JSON output
"${DOCKER_CMD[@]}" 