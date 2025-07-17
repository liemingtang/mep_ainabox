#!/bin/bash

# Folder Scanner Wrapper Script
# This script provides an easy way to use the folder scanner utility

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
DRY_RUN=false
RECURSIVE=true
MAX_DEPTH=""
CONCURRENT=5
SAVE_REPORT=""

# Function to show usage
show_usage() {
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "Options:"
    echo "  --dry-run, -d          Show what would be processed without actually processing"
    echo "  --no-recursive         Disable recursive scanning (default: recursive)"
    echo "  --max-depth <depth>    Maximum depth for recursive scanning"
    echo "  --concurrent <num>     Number of concurrent processing tasks (default: 5)"
    echo "  --save-report <file>   Save processing report to specific file"
    echo "  --help, -h             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder"
    echo "  $0 /path/to/folder --dry-run"
    echo "  $0 /path/to/folder --max-depth 3"
    echo "  $0 /path/to/folder --no-recursive"
    echo "  $0 /path/to/folder --concurrent 10 --save-report my_report.json"
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

# Build the command
CMD="python3 $SCRIPT_DIR/folder_scanner.py \"$FOLDER_PATH\""

if [[ "$DRY_RUN" == true ]]; then
    CMD="$CMD --dry-run"
fi

if [[ "$RECURSIVE" == false ]]; then
    CMD="$CMD --no-recursive"
fi

if [[ -n "$MAX_DEPTH" ]]; then
    CMD="$CMD --max-depth $MAX_DEPTH"
fi

if [[ -n "$CONCURRENT" ]]; then
    CMD="$CMD --concurrent $CONCURRENT"
fi

if [[ -n "$SAVE_REPORT" ]]; then
    CMD="$CMD --save-report \"$SAVE_REPORT\""
fi

# Print the command being executed
echo "Executing: $CMD"
echo ""

# Execute the command
eval $CMD 