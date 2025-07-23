#!/bin/bash

# Test script to debug the while loop issue

CORE_PROCESSOR_URL="http://localhost:8001"

echo "Testing get_all_documents function..."

# Get all documents
documents=$(curl -s "$CORE_PROCESSOR_URL/documents" | python3 -c "
import sys, json
try:
    docs = json.load(sys.stdin)
    for doc in docs:
        if doc.get('source') == 'folder_scanner':
            print(f\"{doc['id']}\t{doc['filename']}\t{doc['processing_status']}\")
except:
    pass
")

echo "Documents found:"
echo "$documents"
echo "Total lines: $(echo "$documents" | wc -l)"

echo ""
echo "Testing while loop..."

processed_count=0
failed_count=0

while IFS=$'\t' read -r document_id filename status; do
    if [[ -n "$document_id" ]]; then
        echo "Processing: $filename (ID: $document_id, Status: $status)"
        ((processed_count++))
        echo "Processed count: $processed_count"
        
        # Only process first 3 documents for testing
        if [[ $processed_count -ge 3 ]]; then
            echo "Stopping after 3 documents for testing"
            break
        fi
    fi
done <<< "$documents"

echo "Final count: Processed=$processed_count, Failed=$failed_count" 