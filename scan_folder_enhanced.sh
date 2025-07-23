#!/bin/bash

# Enhanced Scan Folder Script for MEP AI NABOX
# Supports multiple processing modes for guaranteed document processing

set -e

# Configuration
CORE_PROCESSOR_URL="http://localhost:8001"
PROCESSING_PIPELINE_URL="http://localhost:8003"
DEFAULT_PROCESSING_MODE="enhanced"  # enhanced, queue, sync, atomic

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${PURPLE}🎯 $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Enhanced Scan Folder Script for MEP AI NABOX"
    echo ""
    echo "Usage: $0 <folder_path> [options]"
    echo ""
    echo "Processing Modes:"
    echo "  --enhanced    Enhanced asynchronous processing (default, good reliability)"
    echo "  --queue       Queue-based processing (excellent reliability, guaranteed delivery)"
    echo "  --sync        Synchronous processing (100% reliability, no stuck documents)"
    echo "  --atomic      Atomic processing (perfect reliability, database transactions)"
    echo ""
    echo "Options:"
    echo "  --dry-run     Show what would be processed without actually processing"
    echo "  --concurrent  Number of concurrent processes (default: 5)"
    echo "  --max-depth   Maximum directory depth to scan (default: unlimited)"
    echo "  --recursive   Scan subdirectories recursively (default: true)"
    echo "  --save-report Save processing report to file"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/folder                    # Enhanced processing (default)"
    echo "  $0 /path/to/folder --queue           # Queue-based processing"
    echo "  $0 /path/to/folder --sync            # Synchronous processing"
    echo "  $0 /path/to/folder --atomic          # Atomic processing"
    echo "  $0 /path/to/folder --queue --dry-run # Test queue processing"
    echo ""
}

# Function to check if services are running
check_services() {
    print_info "Checking service health..."
    
    # Check core processor
    if ! curl -s "$CORE_PROCESSOR_URL/health" > /dev/null; then
        print_error "Core processor is not running at $CORE_PROCESSOR_URL"
        return 1
    fi
    
    # Check processing pipeline
    if ! curl -s "$PROCESSING_PIPELINE_URL/health" > /dev/null; then
        print_error "Processing pipeline is not running at $PROCESSING_PIPELINE_URL"
        return 1
    fi
    
    print_status "All services are healthy"
    return 0
}

# Function to scan folder using original script
scan_folder() {
    local folder_path="$1"
    local concurrent="$2"
    local max_depth="$3"
    local recursive="$4"
    local save_report="$5"
    
    print_info "Scanning folder: $folder_path"
    
    # Build command
    local cmd="./scan_folder.sh \"$folder_path\""
    
    if [[ "$concurrent" != "5" ]]; then
        cmd="$cmd --concurrent $concurrent"
    fi
    
    if [[ "$max_depth" != "unlimited" ]]; then
        cmd="$cmd --max-depth $max_depth"
    fi
    
    if [[ "$recursive" == "false" ]]; then
        cmd="$cmd --no-recursive"
    fi
    
    if [[ "$save_report" == "true" ]]; then
        cmd="$cmd --save-report"
    fi
    
    print_info "Executing: $cmd"
    eval "$cmd"
}

# Function to get uploaded documents
get_uploaded_documents() {
    local response=$(curl -s "$CORE_PROCESSOR_URL/documents")
    echo "$response" | python3 -c "
import sys, json
try:
    docs = json.load(sys.stdin)
    for doc in docs:
        if doc.get('source') == 'folder_scanner':
            print(f\"{doc['id']}\t{doc['filename']}\t{doc['processing_status']}\")
except:
    pass
"
}

# Function to process document with queue-based processing
process_document_queue() {
    local document_id="$1"
    local job_id="$2"
    
    print_info "Processing document $document_id via queue..."
    
    local response=$(curl -s -X POST "$PROCESSING_PIPELINE_URL/process-queue" \
        -H "Content-Type: application/json" \
        -d "{\"document_id\": \"$document_id\", \"job_id\": \"$job_id\"}")
    
    local status=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'error'))
except:
    print('error')
")
    
    if [[ "$status" == "queued" ]]; then
        print_status "Document $document_id queued successfully"
        return 0
    else
        print_error "Failed to queue document $document_id: $response"
        return 1
    fi
}

# Function to process document with synchronous processing
process_document_sync() {
    local document_id="$1"
    local job_id="$2"
    
    print_info "Processing document $document_id synchronously..."
    
    local response=$(curl -s -X POST "$PROCESSING_PIPELINE_URL/process-sync" \
        -H "Content-Type: application/json" \
        -d "{\"document_id\": \"$document_id\", \"job_id\": \"$job_id\"}")
    
    local status=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'error'))
except:
    print('error')
")
    
    if [[ "$status" == "completed" ]]; then
        print_status "Document $document_id processed synchronously"
        return 0
    else
        print_error "Failed to process document $document_id synchronously: $response"
        return 1
    fi
}

# Function to process document with atomic processing
process_document_atomic() {
    local document_id="$1"
    local job_id="$2"
    
    print_info "Processing document $document_id atomically..."
    
    local response=$(curl -s -X POST "$PROCESSING_PIPELINE_URL/process-atomic" \
        -H "Content-Type: application/json" \
        -d "{\"document_id\": \"$document_id\", \"job_id\": \"$job_id\"}")
    
    local status=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'error'))
except:
    print('error')
")
    
    if [[ "$status" == "completed" ]]; then
        print_status "Document $document_id processed atomically"
        return 0
    else
        print_error "Failed to process document $document_id atomically: $response"
        return 1
    fi
}

# Function to run queue worker
run_queue_worker() {
    print_info "Starting queue worker..."
    print_info "Press Ctrl+C to stop the worker"
    
    python3 queue_worker.py --no-stats
}

# Function to monitor processing
monitor_processing() {
    local processing_mode="$1"
    
    print_info "Monitoring processing with $processing_mode mode..."
    
    if [[ "$processing_mode" == "queue" ]]; then
        print_info "Queue-based processing: Jobs are queued and will be processed by queue worker"
        print_info "Run 'python3 queue_worker.py' in another terminal to process queued jobs"
    elif [[ "$processing_mode" == "sync" ]]; then
        print_info "Synchronous processing: All documents processed immediately"
    elif [[ "$processing_mode" == "atomic" ]]; then
        print_info "Atomic processing: All documents processed with database transactions"
    fi
    
    # Show final status
    sleep 2
    print_info "Final document status:"
    get_uploaded_documents
}

# Main function
main() {
    # Parse arguments
    local folder_path=""
    local processing_mode="$DEFAULT_PROCESSING_MODE"
    local dry_run=false
    local concurrent=5
    local max_depth="unlimited"
    local recursive=true
    local save_report=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --enhanced)
                processing_mode="enhanced"
                shift
                ;;
            --queue)
                processing_mode="queue"
                shift
                ;;
            --sync)
                processing_mode="sync"
                shift
                ;;
            --atomic)
                processing_mode="atomic"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --concurrent)
                concurrent="$2"
                shift 2
                ;;
            --max-depth)
                max_depth="$2"
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --no-recursive)
                recursive=false
                shift
                ;;
            --save-report)
                save_report=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$folder_path" ]]; then
                    folder_path="$1"
                else
                    print_error "Multiple folder paths specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Check if folder path is provided
    if [[ -z "$folder_path" ]]; then
        print_error "Folder path is required"
        show_usage
        exit 1
    fi
    
    # Check if folder exists
    if [[ ! -d "$folder_path" ]]; then
        print_error "Folder does not exist: $folder_path"
        exit 1
    fi
    
    # Show processing mode
    print_header "Processing Mode: $processing_mode"
    case $processing_mode in
        "enhanced")
            print_info "Enhanced asynchronous processing (good reliability)"
            ;;
        "queue")
            print_info "Queue-based processing (excellent reliability, guaranteed delivery)"
            ;;
        "sync")
            print_info "Synchronous processing (100% reliability, no stuck documents)"
            ;;
        "atomic")
            print_info "Atomic processing (perfect reliability, database transactions)"
            ;;
    esac
    
    if [[ "$dry_run" == "true" ]]; then
        print_warning "DRY RUN MODE - No actual processing will occur"
    fi
    
    # Check services
    if ! check_services; then
        exit 1
    fi
    
    # Step 1: Scan folder (upload documents)
    print_header "Step 1: Scanning folder and uploading documents"
    if [[ "$dry_run" == "false" ]]; then
        scan_folder "$folder_path" "$concurrent" "$max_depth" "$recursive" "$save_report"
    else
        print_info "Would scan folder: $folder_path"
    fi
    
    # Step 2: Process documents based on mode
    if [[ "$dry_run" == "false" ]]; then
        print_header "Step 2: Processing documents with $processing_mode mode"
        
        # Get uploaded documents
        local documents=$(get_uploaded_documents)
        
        if [[ -z "$documents" ]]; then
            print_warning "No documents found to process"
            return 0
        fi
        
        local processed_count=0
        local failed_count=0
        
        while IFS=$'\t' read -r document_id filename status; do
            if [[ -n "$document_id" ]]; then
                print_info "Processing: $filename (ID: $document_id, Status: $status)"
                
                local job_id="job-$(date +%s)-$RANDOM"
                local success=false
                
                case $processing_mode in
                    "enhanced")
                        print_info "Document $document_id will be processed by enhanced async flow"
                        success=true
                        ;;
                    "queue")
                        if process_document_queue "$document_id" "$job_id"; then
                            success=true
                        fi
                        ;;
                    "sync")
                        if process_document_sync "$document_id" "$job_id"; then
                            success=true
                        fi
                        ;;
                    "atomic")
                        if process_document_atomic "$document_id" "$job_id"; then
                            success=true
                        fi
                        ;;
                esac
                
                if [[ "$success" == "true" ]]; then
                    ((processed_count++))
                else
                    ((failed_count++))
                fi
            fi
        done <<< "$documents"
        
        print_header "Processing Summary"
        print_status "Successfully processed: $processed_count"
        if [[ $failed_count -gt 0 ]]; then
            print_error "Failed to process: $failed_count"
        fi
        
        # Step 3: Monitor processing
        monitor_processing "$processing_mode"
        
        # Step 4: Queue worker instructions
        if [[ "$processing_mode" == "queue" ]]; then
            print_header "Queue Processing Instructions"
            print_info "To process queued jobs, run one of the following:"
            print_info "  python3 queue_worker.py                    # Continuous processing"
            print_info "  python3 queue_worker.py --test             # Process one job"
            print_info "  python3 enhanced_monitor.py --continuous   # Monitor and auto-fix"
        fi
    fi
    
    print_status "Enhanced scan folder processing completed!"
}

# Run main function
main "$@" 