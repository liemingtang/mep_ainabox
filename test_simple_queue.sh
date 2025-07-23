#!/bin/bash

# Simple test script for queue processing

CORE_PROCESSOR_URL="http://localhost:8001"
PROCESSING_PIPELINE_URL="http://localhost:8003"

echo "Testing simple queue processing..."

# Get first document
document_id=$(curl -s "$CORE_PROCESSOR_URL/documents" | python3 -c "
import sys, json
try:
    docs = json.load(sys.stdin)
    for doc in docs:
        if doc.get('source') == 'folder_scanner':
            print(doc['id'])
            break
except:
    pass
")

if [[ -n "$document_id" ]]; then
    echo "Processing document: $document_id"
    
    # Generate job ID
    job_id=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
    echo "Job ID: $job_id"
    
    # Process document
    echo "Sending request to processing pipeline..."
    response=$(curl -s --max-time 10 -X POST "$PROCESSING_PIPELINE_URL/process-queue" \
        -H "Content-Type: application/json" \
        -d "{\"document_id\": \"$document_id\", \"job_id\": \"$job_id\"}")
    
    echo "Response: $response"
    
    # Check status
    status=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'error'))
except:
    print('error')
")
    
    echo "Status: $status"
    
    if [[ "$status" == "queued" ]]; then
        echo "SUCCESS: Document queued successfully"
    else
        echo "ERROR: Failed to queue document"
    fi
else
    echo "No documents found"
fi 