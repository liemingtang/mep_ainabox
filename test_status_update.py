#!/usr/bin/env python3
"""
Test script to trigger document processing and monitor status updates
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

async def test_status_update():
    """Test the status update process"""
    print("🧪 Starting status update test...")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Get a document that's stuck in processing
        print("\n📋 Step 1: Getting stuck documents...")
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        documents = response.json()
        
        # Find a document that's stuck in processing
        stuck_docs = [doc for doc in documents if doc.get('processing_status') == 'processing']
        
        if not stuck_docs:
            print("❌ No stuck documents found")
            return
        
        test_doc = stuck_docs[0]
        print(f"📄 Found stuck document: {test_doc['filename']} (ID: {test_doc['id']})")
        
        # Step 2: Check current status
        print(f"\n📋 Step 2: Checking current status for {test_doc['id']}...")
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{test_doc['id']}/processing-status")
        response.raise_for_status()
        status_data = response.json()
        print(f"📊 Current status: {status_data}")
        
        # Step 3: Try to manually trigger status update
        print(f"\n📋 Step 3: Manually triggering status update for {test_doc['id']}...")
        
        # Get the first job ID
        jobs = status_data.get('processing_jobs', [])
        if not jobs:
            print("❌ No jobs found for document")
            return
        
        job_id = jobs[0]['id']
        print(f"🔧 Using job ID: {job_id}")
        
        # Try to update job status
        print(f"\n🔧 Updating job status to 'completed'...")
        try:
            response = await client.post(
                f"{PROCESSING_PIPELINE_URL}/jobs/{test_doc['id']}/status",
                json={
                    "status": "completed",
                    "result_data": {
                        "text_extracted": True,
                        "embeddings_generated": True,
                        "processing_time": 1.5,
                        "test": True
                    }
                },
                timeout=10.0
            )
            print(f"✅ Job status update response: {response.status_code}")
            print(f"📄 Response body: {response.text}")
        except Exception as e:
            print(f"❌ Job status update failed: {e}")
        
        # Try to update document status
        print(f"\n🔧 Updating document status to 'completed'...")
        try:
            response = await client.post(
                f"{CORE_PROCESSOR_URL}/documents/{test_doc['id']}/status",
                json={
                    "processing_status": "completed"
                },
                timeout=10.0
            )
            print(f"✅ Document status update response: {response.status_code}")
            print(f"📄 Response body: {response.text}")
        except Exception as e:
            print(f"❌ Document status update failed: {e}")
        
        # Step 4: Check status again
        print(f"\n📋 Step 4: Checking status after update...")
        await asyncio.sleep(1)
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{test_doc['id']}/processing-status")
        response.raise_for_status()
        status_data = response.json()
        print(f"📊 Updated status: {status_data}")
        
        print(f"\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_status_update()) 