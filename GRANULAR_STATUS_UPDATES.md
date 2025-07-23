# Granular Status Updates for Document Processing

## Overview

This document describes the enhanced status update system implemented to provide better visibility into document processing and help debug stuck processing issues.

## Changes Made

### 1. Enhanced Processing Pipeline Status Updates

All processing modes now provide granular status updates after each step:

#### **Standard Processing** (`/process`)
- **Step 1/5**: Initialize processing (10% progress)
- **Step 2/5**: Document info retrieval (20% progress)
- **Step 3/5**: Text extraction (40% progress)
- **Step 4/5**: Embedding generation (70% progress)
- **Step 5/5**: Finalize processing (90-100% progress)

#### **Synchronous Processing** (`/process-sync`)
- **Step 1/5**: Initialize SYNC processing (10% progress)
- **Step 2/5**: Document info retrieval (20% progress)
- **Step 3/5**: Text extraction (40% progress)
- **Step 4/5**: Embedding generation (70% progress)
- **Step 5/5**: Finalize SYNC processing (90-100% progress)

#### **Queue Processing** (`/process-queue-worker`)
- **Step 1/4**: Initialize queue processing (10% progress)
- **Step 2/4**: Text extraction (30% progress)
- **Step 3/4**: Embedding generation (60% progress)
- **Step 4/4**: Finalize queue processing (90-100% progress)

#### **Atomic Processing** (`/process-atomic`)
- **Step 1/5**: Initialize ATOMIC processing (10% progress)
- **Step 2/5**: Document info retrieval (20% progress)
- **Step 3/5**: Text extraction (40% progress)
- **Step 4/5**: Embedding generation (70% progress)
- **Step 5/5**: Finalize ATOMIC processing (90-100% progress)

### 2. Status Update Functions

Each step now calls:
```python
await update_job_status(job_id, "processing", {
    "current_step": "step_name",
    "progress": percentage,
    "message": "Human readable message"
})
await update_document_status(document_id, "processing")
```

### 3. Error Handling

Enhanced error handling with detailed status updates:
- Each step has specific error handling
- Failed steps update both job and document status
- Error messages are logged and stored
- Processing stops immediately on failure

## New Monitoring Tools

### 1. Real-time Status Monitor

A new script `monitor_processing_status.py` provides comprehensive monitoring:

```bash
# Monitor all documents
python3 monitor_processing_status.py

# Monitor specific document
python3 monitor_processing_status.py --document <document_id>

# Watch mode (continuous updates)
python3 monitor_processing_status.py --watch

# Filter by status
python3 monitor_processing_status.py --processing
python3 monitor_processing_status.py --failed
python3 monitor_processing_status.py --completed
python3 monitor_processing_status.py --pending

# Check for stuck documents
python3 monitor_processing_status.py --check-stuck
```

### 2. Features of the Monitor

- **Real-time updates**: Watch mode refreshes every 5 seconds
- **Color-coded status**: Different colors for different statuses
- **Detailed information**: Shows progress, current step, timestamps
- **Error tracking**: Displays error messages and failure reasons
- **Stuck document detection**: Identifies documents that may be stuck
- **Job-level details**: Shows individual job status and results

## How to Debug Stuck Processing

### 1. Identify Stuck Documents

```bash
# Check for stuck documents
python3 monitor_processing_status.py --check-stuck

# Monitor processing documents
python3 monitor_processing_status.py --processing
```

### 2. Monitor Specific Document

```bash
# Get detailed info about a specific document
python3 monitor_processing_status.py --document <document_id>
```

### 3. Real-time Monitoring

```bash
# Watch all documents in real-time
python3 monitor_processing_status.py --watch
```

### 4. Check Processing Pipeline Status

```bash
# Check processing pipeline health
curl http://localhost:8003/health

# Get stuck documents from pipeline
curl http://localhost:8003/state/stuck-documents
```

## Status Information Available

### Document Status
- `pending`: Document uploaded, waiting to be processed
- `processing`: Document is currently being processed
- `completed`: Document processing finished successfully
- `failed`: Document processing failed

### Processing Steps
- `initialized`: Processing pipeline started
- `document_info_retrieval`: Getting document metadata
- `text_extraction`: Extracting text from document
- `embedding_generation`: Generating vector embeddings
- `finalizing`: Storing results and completing

### Progress Tracking
- Progress percentage (0-100%)
- Current step name
- Human-readable status messages
- Timestamps for each update

## API Endpoints for Status

### Core Processor
```bash
# Get all documents
GET http://localhost:8001/documents

# Get specific document
GET http://localhost:8001/documents/{document_id}

# Get document processing status
GET http://localhost:8001/documents/{document_id}/processing-status
```

### Processing Pipeline
```bash
# Get job status
GET http://localhost:8003/status/{job_id}

# Get stuck documents
GET http://localhost:8003/state/stuck-documents

# Get document state
GET http://localhost:8003/state/{document_id}
```

## Troubleshooting Common Issues

### 1. Documents Stuck in "processing" Status

**Check:**
```bash
# Look for stuck documents
python3 monitor_processing_status.py --check-stuck

# Check processing pipeline logs
docker logs mep-processing-pipeline
```

**Possible causes:**
- Processing pipeline service down
- Database connection issues
- File access problems
- Memory/CPU constraints

### 2. Documents Stuck in "pending" Status

**Check:**
```bash
# Check if processing pipeline is running
curl http://localhost:8003/health

# Check core processor logs
docker logs mep-core-processor
```

**Possible causes:**
- Processing pipeline not receiving requests
- Job queue issues
- Network connectivity problems

### 3. Failed Documents

**Check:**
```bash
# Get failed documents
python3 monitor_processing_status.py --failed

# Check specific failed document
python3 monitor_processing_status.py --document <failed_document_id>
```

**Common failure reasons:**
- Invalid file format
- File too large
- Text extraction failed
- Embedding generation failed
- Database errors

## Best Practices

### 1. Regular Monitoring
- Use watch mode during processing: `python3 monitor_processing_status.py --watch`
- Check for stuck documents periodically
- Monitor system resources (CPU, memory, disk)

### 2. Debugging Workflow
1. Identify stuck/failed documents
2. Check specific document details
3. Review processing pipeline logs
4. Check system resources
5. Restart services if needed

### 3. Log Analysis
- Monitor processing pipeline logs: `docker logs -f mep-processing-pipeline`
- Check core processor logs: `docker logs -f mep-core-processor`
- Look for error patterns and timestamps

## Example Usage

### Monitor Processing in Real-time
```bash
# Start real-time monitoring
python3 monitor_processing_status.py --watch

# In another terminal, upload documents
./scan_folder_enhanced.sh /path/to/folder --queue
```

### Debug a Stuck Document
```bash
# Find stuck documents
python3 monitor_processing_status.py --check-stuck

# Get details about specific document
python3 monitor_processing_status.py --document 49c28c29-1634-4c1b-8d32-56c4d11f1f40

# Check processing pipeline status
curl http://localhost:8003/state/49c28c29-1634-4c1b-8d32-56c4d11f1f40
```

This enhanced status update system provides comprehensive visibility into document processing and makes it much easier to identify and resolve stuck processing issues. 