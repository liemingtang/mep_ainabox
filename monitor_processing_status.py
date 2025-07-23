#!/usr/bin/env python3
"""
Real-time Document Processing Status Monitor

This script monitors the processing status of documents in the MEP AI NABOX system
and helps identify stuck or failed documents.

Usage:
    python3 monitor_processing_status.py                    # Monitor all documents
    python3 monitor_processing_status.py --document <id>    # Monitor specific document
    python3 monitor_processing_status.py --stuck            # Show only stuck documents
    python3 monitor_processing_status.py --failed           # Show only failed documents
    python3 monitor_processing_status.py --processing       # Show only processing documents
    python3 monitor_processing_status.py --watch            # Watch mode (continuous updates)
"""

import asyncio
import httpx
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import argparse

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

def print_colored(text: str, color: str = NC, end: str = "\n"):
    """Print colored text"""
    print(f"{color}{text}{NC}", end=end)

def print_header(text: str):
    """Print header text"""
    print_colored(f"\n{'='*60}", PURPLE)
    print_colored(f"  {text}", PURPLE)
    print_colored(f"{'='*60}", PURPLE)

def print_status(status: str):
    """Print status with appropriate color"""
    if status == "completed":
        print_colored(f"✅ {status}", GREEN)
    elif status == "processing":
        print_colored(f"🔄 {status}", YELLOW)
    elif status == "failed":
        print_colored(f"❌ {status}", RED)
    elif status == "pending":
        print_colored(f"⏳ {status}", BLUE)
    elif status == "initializing":
        print_colored(f"🚀 {status}", BLUE)
    elif status == "generating_embeddings":
        print_colored(f"🧠 {status}", CYAN)
    elif status == "finalizing":
        print_colored(f"🎯 {status}", PURPLE)
    elif status == "text_extraction_failed":
        print_colored(f"📝 {status}", RED)
    elif status == "embedding_generation_failed":
        print_colored(f"🧠 {status}", RED)
    else:
        print_colored(f"❓ {status}", CYAN)

async def get_all_documents() -> List[Dict]:
    """Get all documents from the core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print_colored(f"Error getting documents: {e}", RED)
        return []

async def get_document_processing_status(document_id: str) -> Optional[Dict]:
    """Get processing status for a specific document"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print_colored(f"Error getting processing status for {document_id}: {e}", RED)
        return None

async def get_job_status(job_id: str) -> Optional[Dict]:
    """Get job status from processing pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PROCESSING_PIPELINE_URL}/status/{job_id}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print_colored(f"Error getting job status for {job_id}: {e}", RED)
        return None

def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display"""
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def display_document_info(doc: Dict, detailed: bool = False):
    """Display document information"""
    print_colored(f"\n📄 Document: {doc.get('filename', 'Unknown')}", BLUE)
    print_colored(f"   ID: {doc.get('id', 'Unknown')}", CYAN)
    print_colored(f"   Status: ", end="")
    print_status(doc.get('processing_status', 'unknown'))
    print_colored(f"   Created: {format_timestamp(doc.get('created_at', ''))}", CYAN)
    print_colored(f"   Updated: {format_timestamp(doc.get('updated_at', ''))}", CYAN)
    
    if detailed:
        print_colored(f"   File Path: {doc.get('file_path', 'Unknown')}", CYAN)
        print_colored(f"   File Size: {doc.get('file_size', 0)} bytes", CYAN)
        print_colored(f"   MIME Type: {doc.get('mime_type', 'Unknown')}", CYAN)
        print_colored(f"   Document Type: {doc.get('document_type', 'Unknown')}", CYAN)
        
        if doc.get('error_message'):
            print_colored(f"   Error: {doc.get('error_message')}", RED)

def display_processing_details(processing_status: Dict):
    """Display detailed processing information"""
    if not processing_status:
        return
    
    print_colored(f"\n🔧 Processing Details:", BLUE)
    
    # Document status
    doc_status = processing_status.get('processing_status', 'unknown')
    print_colored(f"   Document Status: ", end="")
    print_status(doc_status)
    
    # Processing jobs
    jobs = processing_status.get('processing_jobs', [])
    if jobs:
        print_colored(f"   Processing Jobs: {len(jobs)}", CYAN)
        for i, job in enumerate(jobs, 1):
            print_colored(f"     Job {i}:", CYAN)
            print_colored(f"       ID: {job.get('id', 'Unknown')}", CYAN)
            print_colored(f"       Status: ", end="")
            print_status(job.get('status', 'unknown'))
            print_colored(f"       Started: {format_timestamp(job.get('started_at', ''))}", CYAN)
            print_colored(f"       Completed: {format_timestamp(job.get('completed_at', ''))}", CYAN)
            
            if job.get('error_message'):
                print_colored(f"       Error: {job.get('error_message')}", RED)
            
            # Job results
            results = job.get('result_data', {})
            if results:
                print_colored(f"       Results:", CYAN)
                for key, value in results.items():
                    if key in ['text_content']:  # Skip large content
                        print_colored(f"         {key}: [Content omitted]", CYAN)
                    else:
                        print_colored(f"         {key}: {value}", CYAN)

async def monitor_specific_document(document_id: str):
    """Monitor a specific document"""
    print_header(f"Monitoring Document: {document_id}")
    
    # Get document info
    documents = await get_all_documents()
    document = next((doc for doc in documents if doc.get('id') == document_id), None)
    
    if not document:
        print_colored(f"Document {document_id} not found", RED)
        return
    
    display_document_info(document, detailed=True)
    
    # Get processing status
    processing_status = await get_document_processing_status(document_id)
    display_processing_details(processing_status)
    
    # Get job status if available
    if processing_status and processing_status.get('processing_jobs'):
        job_id = processing_status['processing_jobs'][0].get('id')
        if job_id:
            print_colored(f"\n🔍 Job Details:", BLUE)
            job_status = await get_job_status(job_id)
            if job_status:
                print_colored(f"   Job ID: {job_status.get('job_id', 'Unknown')}", CYAN)
                print_colored(f"   Status: ", end="")
                print_status(job_status.get('status', 'unknown'))
                print_colored(f"   Progress: {job_status.get('progress', 0)}%", CYAN)
                print_colored(f"   Current Step: {job_status.get('current_step', 'Unknown')}", CYAN)
                print_colored(f"   Started: {format_timestamp(job_status.get('started_at', ''))}", CYAN)
                
                if job_status.get('error_message'):
                    print_colored(f"   Error: {job_status.get('error_message')}", RED)

async def monitor_all_documents(filter_status: Optional[str] = None):
    """Monitor all documents with optional status filter"""
    print_header("Document Processing Status Monitor")
    
    documents = await get_all_documents()
    
    if not documents:
        print_colored("No documents found", YELLOW)
        return
    
    # Filter documents if needed
    if filter_status:
        documents = [doc for doc in documents if doc.get('processing_status') == filter_status]
        if not documents:
            print_colored(f"No documents with status '{filter_status}' found", YELLOW)
            return
    
    # Group by status
    status_groups = {}
    for doc in documents:
        status = doc.get('processing_status', 'unknown')
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(doc)
    
    # Display summary
    print_colored(f"\n📊 Summary:", BLUE)
    total_docs = len(documents)
    print_colored(f"   Total Documents: {total_docs}", CYAN)
    
    for status, docs in status_groups.items():
        print_colored(f"   ", end="")
        print_status(status)
        print_colored(f" ({len(docs)} documents)", CYAN)
    
    # Display documents by status (in order of processing flow)
    status_order = [
        'pending', 'initializing', 'generating_embeddings', 'finalizing', 
        'completed', 'text_extraction_failed', 'embedding_generation_failed', 'failed'
    ]
    
    for status in status_order:
        if status in status_groups:
            print_colored(f"\n{status.upper().replace('_', ' ')} Documents ({len(status_groups[status])}):", BLUE)
            for doc in status_groups[status]:
                display_document_info(doc, detailed=False)

async def watch_mode():
    """Continuous monitoring mode"""
    print_header("Real-time Processing Monitor (Press Ctrl+C to stop)")
    
    try:
        while True:
            # Clear screen (works on most terminals)
            print("\033[2J\033[H", end="")
            
            print_header(f"Real-time Processing Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await monitor_all_documents()
            
            print_colored(f"\n🔄 Refreshing in 5 seconds... (Press Ctrl+C to stop)", YELLOW)
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print_colored(f"\n\n👋 Monitoring stopped", GREEN)

async def check_stuck_documents():
    """Check for potentially stuck documents"""
    print_header("Stuck Documents Check")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PROCESSING_PIPELINE_URL}/state/stuck-documents")
            response.raise_for_status()
            stuck_data = response.json()
            
            stuck_docs = stuck_data.get('stuck_documents', [])
            
            if not stuck_docs:
                print_colored("✅ No stuck documents found", GREEN)
                return
            
            print_colored(f"⚠️  Found {len(stuck_docs)} potentially stuck documents:", YELLOW)
            
            for doc in stuck_docs:
                print_colored(f"\n📄 Document: {doc.get('document_id', 'Unknown')}", BLUE)
                print_colored(f"   Status: {doc.get('status', 'Unknown')}", CYAN)
                print_colored(f"   Current Step: {doc.get('current_step', 'Unknown')}", CYAN)
                print_colored(f"   Started: {format_timestamp(doc.get('started_at', ''))}", CYAN)
                print_colored(f"   Updated: {format_timestamp(doc.get('updated_at', ''))}", CYAN)
                
                if doc.get('error_message'):
                    print_colored(f"   Error: {doc.get('error_message')}", RED)
                    
    except Exception as e:
        print_colored(f"Error checking stuck documents: {e}", RED)

def main():
    parser = argparse.ArgumentParser(description="Monitor document processing status")
    parser.add_argument("--document", "-d", help="Monitor specific document ID")
    parser.add_argument("--stuck", action="store_true", help="Show only stuck documents")
    parser.add_argument("--failed", action="store_true", help="Show only failed documents")
    parser.add_argument("--processing", action="store_true", help="Show only processing documents")
    parser.add_argument("--pending", action="store_true", help="Show only pending documents")
    parser.add_argument("--completed", action="store_true", help="Show only completed documents")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch mode (continuous updates)")
    parser.add_argument("--check-stuck", action="store_true", help="Check for stuck documents")
    
    args = parser.parse_args()
    
    # Determine what to monitor
    if args.document:
        asyncio.run(monitor_specific_document(args.document))
    elif args.watch:
        asyncio.run(watch_mode())
    elif args.check_stuck:
        asyncio.run(check_stuck_documents())
    else:
        # Determine filter
        filter_status = None
        if args.stuck:
            print_colored("Note: Using --check-stuck for better stuck document detection", YELLOW)
            asyncio.run(check_stuck_documents())
            return
        elif args.failed:
            filter_status = "failed"
        elif args.processing:
            filter_status = "processing"
        elif args.pending:
            filter_status = "pending"
        elif args.completed:
            filter_status = "completed"
        
        asyncio.run(monitor_all_documents(filter_status))

if __name__ == "__main__":
    main() 