#!/usr/bin/env python3
"""
Test script to verify queue processing fix
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

async def test_queue_processing_fix():
    """Test that queue processing doesn't reset completed documents"""
    print("🧪 Testing queue processing fix...")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Get current document statuses
        print("\n📋 Step 1: Getting current document statuses...")
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        documents = response.json()
        
        # Count completed vs processing
        completed_docs = [doc for doc in documents if doc.get('processing_status') == 'completed']
        processing_docs = [doc for doc in documents if doc.get('processing_status') == 'processing']
        
        print(f"📊 Current status:")
        print(f"   ✅ Completed: {len(completed_docs)}")
        print(f"   🔄 Processing: {len(processing_docs)}")
        
        if completed_docs:
            print(f"   📄 Completed documents:")
            for doc in completed_docs:
                print(f"      - {doc['filename']} (ID: {doc['id']})")
        
        # Step 2: Trigger queue processing multiple times
        print(f"\n📋 Step 2: Triggering queue processing...")
        for i in range(3):
            print(f"   🔄 Trigger {i+1}/3...")
            try:
                response = await client.post(f"{PROCESSING_PIPELINE_URL}/process-queue-worker", timeout=5.0)
                if response.status_code == 200:
                    result = response.json()
                    print(f"      ✅ Result: {result.get('status', 'unknown')}")
                else:
                    print(f"      ❌ Error: {response.status_code}")
            except Exception as e:
                print(f"      ❌ Exception: {e}")
            
            await asyncio.sleep(1)
        
        # Step 3: Check status again
        print(f"\n📋 Step 3: Checking status after queue processing...")
        await asyncio.sleep(2)
        
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        documents_after = response.json()
        
        completed_docs_after = [doc for doc in documents_after if doc.get('processing_status') == 'completed']
        processing_docs_after = [doc for doc in documents_after if doc.get('processing_status') == 'processing']
        
        print(f"📊 Status after queue processing:")
        print(f"   ✅ Completed: {len(completed_docs_after)}")
        print(f"   🔄 Processing: {len(processing_docs_after)}")
        
        if completed_docs_after:
            print(f"   📄 Completed documents:")
            for doc in completed_docs_after:
                print(f"      - {doc['filename']} (ID: {doc['id']})")
        
        # Step 4: Verify fix worked
        print(f"\n📋 Step 4: Verifying fix...")
        if len(completed_docs) <= len(completed_docs_after):
            print(f"✅ SUCCESS: No completed documents were reset!")
            print(f"   Before: {len(completed_docs)} completed")
            print(f"   After: {len(completed_docs_after)} completed")
        else:
            print(f"❌ FAILURE: Completed documents were reset!")
            print(f"   Before: {len(completed_docs)} completed")
            print(f"   After: {len(completed_docs_after)} completed")
        
        print(f"\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_queue_processing_fix()) 