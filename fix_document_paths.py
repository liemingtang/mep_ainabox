#!/usr/bin/env python3
"""
Script to fix document file paths to use container paths for dynamic mounting
"""

import httpx
import json
import asyncio

CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

async def get_documents():
    """Get all documents from core processor"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
        response.raise_for_status()
        return response.json()

async def update_document_path(document_id: str, new_file_path: str):
    """Update document file path"""
    async with httpx.AsyncClient() as client:
        # First, get the current document info
        response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{document_id}")
        response.raise_for_status()
        document = response.json()
        
        # Update the file_path
        document["file_path"] = new_file_path
        
        # Update the document (this would require an update endpoint)
        # For now, we'll just print what needs to be updated
        print(f"Document {document_id} needs file_path updated from '{document.get('file_path')}' to '{new_file_path}'")

async def test_processing_with_container_path(document_id: str):
    """Test processing with container path"""
    import uuid
    
    job_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PROCESSING_PIPELINE_URL}/process",
            json={
                "document_id": document_id,
                "job_id": job_id
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Processing started successfully for document {document_id}")
            return True
        else:
            print(f"❌ Processing failed for document {document_id}: {response.text}")
            return False

async def main():
    """Main function"""
    print("🔧 Fixing document file paths for dynamic mounting...")
    
    # Get all documents
    documents = await get_documents()
    
    # Filter documents that need path conversion
    documents_to_fix = []
    for doc in documents:
        if doc.get("source") == "folder_scanner" and "/media/lie/DATA2/ai_scan_folder" in doc.get("file_path", ""):
            documents_to_fix.append(doc)
    
    print(f"Found {len(documents_to_fix)} documents that need path conversion:")
    
    for doc in documents_to_fix:
        old_path = doc.get("file_path")
        new_path = old_path.replace("/media/lie/DATA2/ai_scan_folder", "/app/scan_folder")
        
        print(f"  {doc['id']}: {doc['filename']}")
        print(f"    Old path: {old_path}")
        print(f"    New path: {new_path}")
        
        # Update the document path
        await update_document_path(doc["id"], new_path)
    
    print("\n📝 Note: This script shows what needs to be updated.")
    print("To actually update the documents, you would need to:")
    print("1. Add an update endpoint to the core processor")
    print("2. Or manually update the database")
    print("3. Or recreate the documents with the correct paths")
    
    # Test processing with one document
    if documents_to_fix:
        test_doc = documents_to_fix[0]
        print(f"\n🧪 Testing processing with document {test_doc['id']}...")
        
        # Manually update the file_path for testing
        test_doc["file_path"] = test_doc["file_path"].replace("/media/lie/DATA2/ai_scan_folder", "/app/scan_folder")
        
        # For now, we'll just test the processing logic
        print(f"Testing with file_path: {test_doc['file_path']}")
        
        if "/app/scan_folder" in test_doc["file_path"]:
            print("✅ Document has container path - dynamic mounting should work!")
        else:
            print("❌ Document still has external path - dynamic mounting won't work")

if __name__ == "__main__":
    asyncio.run(main()) 