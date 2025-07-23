#!/usr/bin/env python3
"""
Fix documents that have been processed but still show "processing" status
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"

async def fix_processing_status():
    """Fix documents that have been processed but still show processing status"""
    print("🔧 Fixing processing status for completed documents...")
    
    async with httpx.AsyncClient() as client:
        # Get all documents
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        documents = response.json()
        
        # Find documents that are marked as processing but have been processed
        documents_to_fix = []
        for doc in documents:
            if (doc.get('processing_status') == 'processing' and 
                doc.get('processed_at') and 
                not doc.get('error_message')):
                documents_to_fix.append(doc)
        
        print(f"📋 Found {len(documents_to_fix)} documents that need status fix:")
        
        fixed_count = 0
        for doc in documents_to_fix:
            print(f"   - {doc['filename']} (ID: {doc['id']})")
            print(f"     Processed at: {doc['processed_at']}")
            
            # Update status to completed
            try:
                update_response = await client.post(
                    f"{CORE_PROCESSOR_URL}/documents/{doc['id']}/status",
                    json={"status": "completed"}
                )
                update_response.raise_for_status()
                print(f"     ✅ Status updated to completed")
                fixed_count += 1
            except Exception as e:
                print(f"     ❌ Failed to update status: {e}")
        
        print(f"\n📊 Summary:")
        print(f"   Total documents to fix: {len(documents_to_fix)}")
        print(f"   Successfully fixed: {fixed_count}")
        print(f"   Failed: {len(documents_to_fix) - fixed_count}")
        
        if fixed_count > 0:
            print(f"\n✅ Successfully fixed {fixed_count} document statuses!")
        else:
            print(f"\nℹ️  No documents needed fixing.")

if __name__ == "__main__":
    asyncio.run(fix_processing_status()) 