#!/bin/bash

# Script to check files uploaded via the watch folder
# Usage: ./check_uploaded_files.sh [option]

CORE_URL="http://localhost:8001"
WATCHER_URL="http://localhost:8009"

echo "=== MEP AinaBox File Upload Checker ==="
echo

case "${1:-all}" in
    "all")
        echo "📋 All uploaded files:"
        curl -s -X GET "$CORE_URL/documents" | jq -r '.[] | "• \(.filename) (\(.processing_status)) - \(.created_at)"'
        ;;
    "watch")
        echo "📁 Files uploaded via watch folder:"
        curl -s -X GET "$CORE_URL/documents" | jq -r '[.[] | select(.file_path | contains("/app/watch_folder"))] | .[] | "• \(.filename) (\(.processing_status)) - \(.created_at)"'
        ;;
    "status")
        echo "📊 Processing status summary:"
        curl -s -X GET "$CORE_URL/documents" | jq -r '[.[] | select(.file_path | contains("/app/watch_folder"))] | group_by(.processing_status) | .[] | "\(.[0].processing_status): \(length) files"'
        ;;
    "recent")
        echo "🕒 Recent uploads (last 5):"
        curl -s -X GET "$CORE_URL/documents" | jq -r '[.[] | select(.file_path | contains("/app/watch_folder"))] | sort_by(.created_at) | reverse | .[0:5] | .[] | "• \(.filename) (\(.processing_status)) - \(.created_at)"'
        ;;
    "failed")
        echo "❌ Failed uploads:"
        curl -s -X GET "$CORE_URL/documents" | jq -r '[.[] | select(.file_path | contains("/app/watch_folder") and .processing_status == "failed")] | .[] | "• \(.filename) - \(.error_message // "Unknown error")"'
        ;;
    "watcher")
        echo "👀 File watcher status:"
        curl -s -X GET "$WATCHER_URL/api/v1/watch/status" | jq -r '"Status: \(.status)\nWatching: \(.watch_paths)\nProcessed: \(.processed_files_count)\nErrors: \(.error_files_count)\nLast Activity: \(.last_activity)"'
        ;;
    "count")
        echo "📈 File counts:"
        TOTAL=$(curl -s -X GET "$CORE_URL/documents" | jq 'length')
        WATCH=$(curl -s -X GET "$CORE_URL/documents" | jq '[.[] | select(.file_path | contains("/app/watch_folder"))] | length')
        echo "Total files: $TOTAL"
        echo "Watch folder files: $WATCH"
        ;;
    "help")
        echo "Usage: $0 [option]"
        echo
        echo "Options:"
        echo "  all     - Show all uploaded files"
        echo "  watch   - Show only watch folder files"
        echo "  status  - Show processing status summary"
        echo "  recent  - Show 5 most recent uploads"
        echo "  failed  - Show failed uploads with errors"
        echo "  watcher - Show file watcher status"
        echo "  count   - Show file counts"
        echo "  help    - Show this help"
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use '$0 help' for available options"
        ;;
esac

echo 