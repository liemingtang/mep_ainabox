#!/usr/bin/env python3
"""
Test script to demonstrate the new descriptive status system
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

async def test_descriptive_status():
    """Test the new descriptive status system"""
    print("🧪 Testing new descriptive status system...")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Get current document statuses
        print("\n📋 Step 1: Getting current document statuses...")
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        documents = response.json()
        
        # Show all unique statuses
        statuses = set(doc.get('processing_status', 'unknown') for doc in documents)
        print(f"📊 Current statuses in system:")
        for status in sorted(statuses):
            print(f"   - {status}")
        
        # Show documents with new descriptive statuses
        print(f"\n📋 Documents with new descriptive statuses:")
        descriptive_statuses = [
            'initializing', 'generating_embeddings', 'finalizing',
            'text_extraction_failed', 'embedding_generation_failed'
        ]
        
        for status in descriptive_statuses:
            docs_with_status = [doc for doc in documents if doc.get('processing_status') == status]
            if docs_with_status:
                print(f"\n   {status.upper().replace('_', ' ')} ({len(docs_with_status)} documents):")
                for doc in docs_with_status:
                    print(f"      - {doc['filename']} (ID: {doc['id']})")
        
        # Step 2: Show status flow
        print(f"\n📋 Step 2: Expected status flow:")
        print(f"   1. 🚀 initializing")
        print(f"   2. 🧠 generating_embeddings") 
        print(f"   3. 🎯 finalizing")
        print(f"   4. ✅ completed")
        print(f"   Error states:")
        print(f"      📝 text_extraction_failed")
        print(f"      🧠 embedding_generation_failed")
        
        print(f"\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_descriptive_status()) 