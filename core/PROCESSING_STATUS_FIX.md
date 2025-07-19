# Processing Status Issue and Fix

## Problem Description

Documents processed through the `scan_folder.sh` script sometimes get stuck in "processing" status even though all processing steps have been completed successfully.

### Symptoms
- Document shows "processing" status in the dashboard
- Processing job is marked as "completed" 
- All processing steps (text extraction, metadata extraction, embedding generation, entity extraction, relationship mapping) are done
- Document status never updates to "completed"

### Root Cause
The individual processors (text processor, metadata processor, etc.) complete their work but don't properly notify the processing pipeline that they're done. The processing pipeline has the logic to update document status to "completed" but it's not being triggered.

## Solution

### 1. Immediate Fix
Use the provided script to automatically fix stuck documents:

```bash
cd mep_ainabox/core
python3 fix_stuck_documents.py
```

### 2. Manual Fix
For individual documents, you can manually update the status:

```bash
# Get the document ID first
curl -s "http://localhost:8001/documents" | jq '.[] | select(.filename | contains("YOUR_FILENAME")) | .id'

# Update the status to completed
curl -X POST "http://localhost:8001/documents/DOCUMENT_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"processing_status": "completed"}'
```

### 3. Permanent Fix
The code has been updated to prevent this issue:

1. **Text Processor** (`processors/text_processor/main.py`):
   - Added job status update functionality
   - Now properly notifies the processing pipeline when work is completed

2. **Processing Pipeline** (`processing_pipeline/main.py`):
   - Added endpoint to handle job status updates from individual processors
   - Automatically updates document status when jobs complete

## Verification

To verify that a document is truly completed and safe to fix:

1. Check the job status:
```bash
curl -s "http://localhost:8001/documents/DOCUMENT_ID/processing-status" | jq .
```

2. Check the job details:
```bash
curl -s "http://localhost:8001/processing/jobs/JOB_ID" | jq .
```

3. Look for these completed flags in the result_data:
   - `text_extracted`: true
   - `entities_extracted`: true
   - `metadata_extracted`: true
   - `embeddings_generated`: true
   - `relationships_mapped`: true

## Prevention

The fix ensures that:
- Individual processors properly report completion
- Processing pipeline automatically updates document status
- Future documents won't get stuck in processing status

## Monitoring

You can monitor for stuck documents by running the fix script periodically:

```bash
# Add to crontab to run every hour
0 * * * * cd /path/to/mep_ainabox/core && python3 fix_stuck_documents.py >> /var/log/stuck_docs.log 2>&1
``` 