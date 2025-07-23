#!/usr/bin/env python3
"""
Script to fix documents stuck in processing status due to race conditions.
This script identifies documents that are actually completed but stuck in processing status
and updates them to completed status.
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"

async def get_all_documents():
    """Get all documents from the core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CORE_PROCESSOR_URL}/documents", timeout=10.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        return []

async def get_document_processing_status(document_id: str):
    """Get processing status for a specific document"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get processing status for {document_id}: {e}")
        return None

async def get_processing_jobs():
    """Get all processing jobs"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CORE_PROCESSOR_URL}/processing/jobs", timeout=10.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get processing jobs: {e}")
        return []

async def update_document_status(document_id: str, status: str):
    """Update document status"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CORE_PROCESSOR_URL}/documents/{document_id}/status",
                json={"processing_status": status},
                timeout=10.0
            )
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to update document {document_id} status: {e}")
        return False

async def update_job_status(job_id: str, status: str, result_data: dict = None):
    """Update job status"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "status": status,
                "result_data": result_data or {}
            }
            response = await client.post(
                f"{CORE_PROCESSOR_URL}/processing/jobs/{job_id}/status",
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")
        return False

def is_document_completed(processing_status: dict) -> bool:
    """Check if a document is actually completed based on its processing status"""
    try:
        # Check if document has processing jobs
        processing_jobs = processing_status.get("processing_jobs", [])
        
        if not processing_jobs:
            return False
        
        # Check if any job is completed
        for job in processing_jobs:
            job_status = job.get("status")
            result_data = job.get("result_data", {})
            
            # If job is completed and has successful results, document is completed
            if job_status == "completed":
                # Check if the job has successful processing results
                if isinstance(result_data, dict):
                    # Look for indicators of successful processing
                    if (result_data.get("embeddings_generated") or 
                        result_data.get("text_extracted") or
                        result_data.get("status") == "completed"):
                        return True
                elif isinstance(result_data, str):
                    # Try to parse JSON string
                    try:
                        parsed_data = json.loads(result_data)
                        if (parsed_data.get("embeddings_generated") or 
                            parsed_data.get("text_extracted") or
                            parsed_data.get("status") == "completed"):
                            return True
                    except:
                        pass
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if document is completed: {e}")
        return False

async def fix_stuck_documents():
    """Find and fix documents stuck in processing status"""
    logger.info("🔍 Starting stuck document detection and fix...")
    
    # Get all documents
    documents = await get_all_documents()
    if not documents:
        logger.error("No documents found")
        return
    
    logger.info(f"📋 Found {len(documents)} total documents")
    
    # Find documents stuck in processing
    stuck_documents = []
    for doc in documents:
        doc_id = doc.get("id")
        processing_status = doc.get("processing_status")
        
        if processing_status == "processing":
            stuck_documents.append(doc_id)
    
    logger.info(f"⚠️ Found {len(stuck_documents)} documents stuck in processing status")
    
    if not stuck_documents:
        logger.info("✅ No stuck documents found")
        return
    
    # Check each stuck document
    fixed_count = 0
    for doc_id in stuck_documents:
        logger.info(f"🔍 Checking document {doc_id}...")
        
        # Get detailed processing status
        processing_status = await get_document_processing_status(doc_id)
        if not processing_status:
            logger.warning(f"Could not get processing status for {doc_id}")
            continue
        
        # Check if document is actually completed
        if is_document_completed(processing_status):
            logger.info(f"✅ Document {doc_id} is actually completed, fixing status...")
            
            # Get the job ID for this document
            processing_jobs = processing_status.get("processing_jobs", [])
            job_id = None
            if processing_jobs:
                job_id = processing_jobs[0].get("id")
            
            # Update document status to completed
            doc_success = await update_document_status(doc_id, "completed")
            
            # Update job status to completed if we have a job ID
            job_success = True
            if job_id:
                # Get the result data from the job
                result_data = {}
                if processing_jobs:
                    result_data = processing_jobs[0].get("result_data", {})
                
                job_success = await update_job_status(job_id, "completed", result_data)
            
            if doc_success and job_success:
                logger.info(f"✅ Successfully fixed document {doc_id}")
                fixed_count += 1
            else:
                logger.error(f"❌ Failed to fix document {doc_id}")
        else:
            logger.info(f"⏳ Document {doc_id} is still actually processing, leaving as is")
    
    logger.info(f"📊 Fix Summary:")
    logger.info(f"   Total stuck documents: {len(stuck_documents)}")
    logger.info(f"   Fixed documents: {fixed_count}")
    logger.info(f"   Still processing: {len(stuck_documents) - fixed_count}")

async def check_processing_jobs():
    """Check for any processing jobs that might be stuck"""
    logger.info("🔍 Checking processing jobs...")
    
    jobs = await get_processing_jobs()
    if not jobs:
        logger.info("No processing jobs found")
        return
    
    logger.info(f"📋 Found {len(jobs)} processing jobs")
    
    # Check for jobs that might be stuck
    stuck_jobs = []
    for job in jobs:
        job_id = job.get("id")
        status = job.get("status")
        started_at = job.get("started_at")
        
        # Check if job has been running for too long
        if status == "running" and started_at:
            try:
                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                if datetime.now(start_time.tzinfo) - start_time > timedelta(minutes=30):
                    stuck_jobs.append(job_id)
            except:
                pass
    
    if stuck_jobs:
        logger.warning(f"⚠️ Found {len(stuck_jobs)} potentially stuck jobs: {stuck_jobs}")
    else:
        logger.info("✅ No stuck jobs found")

async def main():
    """Main function"""
    logger.info("🚀 Starting stuck document fix script")
    
    try:
        # Check processing jobs first
        await check_processing_jobs()
        
        # Fix stuck documents
        await fix_stuck_documents()
        
        logger.info("✅ Stuck document fix completed")
        
    except Exception as e:
        logger.error(f"💥 Error in stuck document fix: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Script interrupted by user")
    except Exception as e:
        logger.error(f"💥 Script failed: {e}")
        exit(1) 