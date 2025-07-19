#!/usr/bin/env python3
"""
Utility script to fix documents stuck in processing status
"""

import asyncio
import httpx
import json
import sys
from typing import List, Dict, Any

async def get_stuck_documents() -> List[Dict[str, Any]]:
    """Get all documents stuck in processing status"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/documents", timeout=10.0)
        if response.status_code == 200:
            documents = response.json()
            stuck_docs = [
                doc for doc in documents 
                if doc.get("processing_status") == "processing"
            ]
            return stuck_docs
        return []

async def check_job_completion(document_id: str) -> bool:
    """Check if a document's job is actually completed"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://localhost:8001/documents/{document_id}/processing-status",
                timeout=10.0
            )
            if response.status_code == 200:
                status_data = response.json()
                jobs = status_data.get("processing_jobs", [])
                
                # Check if any job is completed
                for job in jobs:
                    if job.get("status") == "completed":
                        # Check if the job result indicates all processing is done
                        job_details = await client.get(
                            f"http://localhost:8001/processing/jobs/{job['id']}",
                            timeout=10.0
                        )
                        if job_details.status_code == 200:
                            job_data = job_details.json()
                            result_data = job_data.get("result_data", {})
                            
                            # Check if all processing steps are completed
                            if (result_data.get("text_extracted") and 
                                result_data.get("entities_extracted") and
                                result_data.get("metadata_extracted") and
                                result_data.get("embeddings_generated") and
                                result_data.get("relationships_mapped")):
                                return True
                return False
        except Exception as e:
            print(f"Error checking job completion for {document_id}: {e}")
            return False

async def fix_document_status(document_id: str, filename: str) -> bool:
    """Fix a document's status from processing to completed"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:8001/documents/{document_id}/status",
                json={"processing_status": "completed"},
                timeout=10.0
            )
            if response.status_code == 200:
                print(f"✓ Fixed: {filename}")
                return True
            else:
                print(f"✗ Failed to fix: {filename} (Status: {response.status_code})")
                return False
        except Exception as e:
            print(f"✗ Error fixing {filename}: {e}")
            return False

async def main():
    """Main function to find and fix stuck documents"""
    print("🔍 Searching for documents stuck in processing status...")
    
    stuck_docs = await get_stuck_documents()
    
    if not stuck_docs:
        print("✅ No documents found stuck in processing status!")
        return
    
    print(f"📋 Found {len(stuck_docs)} documents stuck in processing status:")
    
    fixed_count = 0
    for doc in stuck_docs:
        doc_id = doc["id"]
        filename = doc["filename"]
        created_at = doc["created_at"]
        
        print(f"\n📄 {filename}")
        print(f"   ID: {doc_id}")
        print(f"   Created: {created_at}")
        
        # Check if the job is actually completed
        if await check_job_completion(doc_id):
            print(f"   Status: Job completed, updating document status...")
            if await fix_document_status(doc_id, filename):
                fixed_count += 1
        else:
            print(f"   Status: Job not completed, skipping...")
    
    print(f"\n🎉 Summary: Fixed {fixed_count} out of {len(stuck_docs)} documents")

if __name__ == "__main__":
    asyncio.run(main()) 