#!/usr/bin/env python3
"""
Simple test for document creation only (no processing pipeline)
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path

import httpx


async def test_simple_document_creation():
    """Test document creation without processing pipeline"""
    print("📄 Testing simple document creation...")
    
    # Create a test document with unique content
    test_doc_path = Path("test_document.txt")
    timestamp = int(time.time())
    test_content = f"This is a test document for the MDIS system (timestamp: {timestamp}).\nIt contains some sample text for testing purposes."
    
    print(f"📝 Creating test document with content length: {len(test_content)}")
    
    try:
        with open(test_doc_path, "w") as f:
            f.write(test_content)
        
        # Generate unique file hash
        file_hash = hashlib.sha256(test_content.encode()).hexdigest()
        print(f"🔐 Generated file hash: {file_hash}")
        
        # Test document upload
        document_data = {
            "filename": "test_document.txt",
            "file_path": str(test_doc_path.absolute()),
            "file_size": len(test_content),
            "mime_type": "text/plain",
            "file_hash": file_hash,
            "source": "test",
            "document_type": "txt",
            "company": "Test Company",
            "year": 2024,
            "metadata": {
                "test_key": "test_value",
                "upload_source": "test_script",
                "content_length": len(test_content)
            }
        }
        
        print(f"📤 Uploading document data...")
        
        core_url = "http://localhost:8001"
        timeout = 30.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"🌐 Sending POST request to: {core_url}/documents/upload")
            response = await client.post(
                f"{core_url}/documents/upload",
                json=document_data
            )
            
            print(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Document upload successful!")
                print(f"   - Document ID: {result.get('document_id')}")
                print(f"   - Processing Job ID: {result.get('processing_job_id')}")
                print(f"   - Status: {result.get('status')}")
                print(f"   - Message: {result.get('message')}")
                return True
            else:
                print(f"❌ Document upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Document upload error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up test file
        if test_doc_path.exists():
            test_doc_path.unlink()
            print(f"🧹 Cleaned up test file: {test_doc_path}")


async def main():
    """Main test function"""
    print("🚀 Starting Simple Document Creation Test")
    print("=" * 50)
    
    success = await test_simple_document_creation()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Simple document creation test passed!")
    else:
        print("❌ Simple document creation test failed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main()) 