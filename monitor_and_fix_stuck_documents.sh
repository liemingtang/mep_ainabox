#!/bin/bash

# Monitor and Fix Stuck Documents Script
# This script can be run as a cron job to automatically detect and fix stuck documents

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
LOG_FILE="logs/stuck_documents_monitor.log"
MAX_PROCESSING_TIME_MINUTES=30

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if services are running
check_services() {
    log_message "🔍 Checking if MEP AI NABOX services are running..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_message "❌ Docker is not running"
        return 1
    fi
    
    # Check if core processor is accessible
    if ! curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
        log_message "❌ Core processor is not accessible"
        return 1
    fi
    
    log_message "✅ Services are running"
    return 0
}

# Function to run the stuck documents fixer
run_stuck_documents_fixer() {
    log_message "🚀 Running stuck documents fixer..."
    
    # Run the Python script with real execution (not dry run)
    python3 fix_stuck_documents.py --real --max-time "$MAX_PROCESSING_TIME_MINUTES" 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_message "✅ Stuck documents fixer completed successfully"
    else
        log_message "❌ Stuck documents fixer failed"
        return 1
    fi
}

# Function to clean up old logs
cleanup_logs() {
    log_message "🧹 Cleaning up old log files..."
    
    # Keep only the last 7 days of logs
    find logs/ -name "*.log" -type f -mtime +7 -delete 2>/dev/null || true
    
    log_message "✅ Log cleanup completed"
}

# Main execution
main() {
    log_message "=" * 60
    log_message "🔄 Starting stuck documents monitoring and fix process"
    log_message "=" * 60
    
    # Check if services are running
    if ! check_services; then
        log_message "❌ Services check failed, exiting"
        exit 1
    fi
    
    # Run the stuck documents fixer
    if ! run_stuck_documents_fixer; then
        log_message "❌ Stuck documents fixer failed, exiting"
        exit 1
    fi
    
    # Clean up old logs
    cleanup_logs
    
    log_message "✅ Monitoring and fix process completed successfully"
    log_message "=" * 60
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --dry-run      Run in dry-run mode (don't actually fix documents)"
        echo "  --max-time N   Set maximum processing time in minutes (default: 30)"
        echo ""
        echo "This script monitors for stuck documents and automatically fixes them."
        echo "It can be run as a cron job for continuous monitoring."
        echo ""
        echo "Example cron job (run every 15 minutes):"
        echo "*/15 * * * * /path/to/monitor_and_fix_stuck_documents.sh"
        exit 0
        ;;
    --dry-run)
        log_message "🔍 Running in DRY RUN mode"
        python3 fix_stuck_documents.py --max-time "${2:-30}"
        exit 0
        ;;
    --max-time)
        MAX_PROCESSING_TIME_MINUTES="${2:-30}"
        log_message "⏰ Set maximum processing time to ${MAX_PROCESSING_TIME_MINUTES} minutes"
        ;;
esac

# Run main function
main "$@" 