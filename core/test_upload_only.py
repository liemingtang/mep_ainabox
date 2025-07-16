#!/usr/bin/env python3
"""
Test script for document upload only
"""

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

import httpx


async def test_document_upload():
    """Test document upload functionality with detailed logging"""
    print("📄 Testing document upload...")
    
    # Create a test document with unique content
    test_doc_path = Path("test_document.txt")
    timestamp = int(time.time())
    test_content = f"This is a test document for the MDIS system (timestamp: {timestamp}).\nIt contains some sample text for testing purposes."
    
    print(f"📝 Creating test document with content length: {len(test_content)}")
    print(f"📝 Content preview: {test_content[:50]}...")
    
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
        
        print(f"📤 Uploading document data:")
        print(f"   - Filename: {document_data['filename']}")
        print(f"   - File path: {document_data['file_path']}")
        print(f"   - File size: {document_data['file_size']}")
        print(f"   - File hash: {document_data['file_hash']}")
        print(f"   - Metadata: {document_data['metadata']}")
        
        core_url = "http://localhost:8001"
        timeout = 30.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"🌐 Sending POST request to: {core_url}/documents/upload")
            response = await client.post(
                f"{core_url}/documents/upload",
                json=document_data
            )
            
            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Document upload successful!")
                print(f"   - Document ID: {result.get('document_id')}")
                print(f"   - Processing Job ID: {result.get('processing_job_id')}")
                print(f"   - Status: {result.get('status')}")
                print(f"   - Message: {result.get('message')}")
                
                # Test getting document
                doc_id = result.get('document_id')
                if doc_id:
                    print(f"🔍 Testing document retrieval for ID: {doc_id}")
                    doc_response = await client.get(f"{core_url}/documents/{doc_id}")
                    print(f"📥 Document retrieval status: {doc_response.status_code}")
                    
                    if doc_response.status_code == 200:
                        doc_data = doc_response.json()
                        print(f"✅ Document retrieval successful!")
                        print(f"   - Retrieved filename: {doc_data.get('filename')}")
                        print(f"   - Retrieved status: {doc_data.get('processing_status')}")
                        return True
                    else:
                        print(f"❌ Document retrieval failed: {doc_response.status_code}")
                        print(f"   Response: {doc_response.text}")
                        return False
                else:
                    print("❌ No document ID returned")
                    return False
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
    print("🚀 Starting Document Upload Test")
    print("=" * 50)
    
    success = await test_document_upload()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Document upload test passed!")
    else:
        print("❌ Document upload test failed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main()) 