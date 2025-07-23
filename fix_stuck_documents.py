#!/usr/bin/env python3
"""
Fix Stuck Documents Script
Detects and fixes documents that are stuck in 'processing' status
"""

import asyncio
import httpx
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

class StuckDocumentFixer:
    """Detect and fix documents stuck in processing status"""
    
    def __init__(self):
        self.core_processor_url = CORE_PROCESSOR_URL
        self.processing_pipeline_url = PROCESSING_PIPELINE_URL
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from the core processor"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.core_processor_url}/documents", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
    async def get_document_processing_status(self, document_id: str) -> Dict[str, Any]:
        """Get detailed processing status for a document"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.core_processor_url}/documents/{document_id}/processing-status",
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get processing status for {document_id}: {e}")
            return {}
    
    async def update_document_status(self, document_id: str, status: str) -> bool:
        """Update document status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.core_processor_url}/documents/{document_id}/status",
                    json={"processing_status": status},
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"✅ Updated document {document_id} status to {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update document {document_id} status: {e}")
            return False
    
    def is_document_stuck(self, document: Dict[str, Any], max_processing_time_minutes: int = 30) -> bool:
        """Check if a document is stuck in processing status"""
        if document.get("processing_status") != "processing":
            return False
        
        # Check if document has been in processing for too long
        created_at = document.get("created_at")
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                time_in_processing = datetime.now(created_time.tzinfo) - created_time
                if time_in_processing > timedelta(minutes=max_processing_time_minutes):
                    return True
            except Exception as e:
                logger.warning(f"Could not parse created_at for document {document.get('id')}: {e}")
        
        return False
    
    def analyze_processing_jobs(self, processing_status: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze processing jobs to determine if document is actually completed"""
        jobs = processing_status.get("processing_jobs", [])
        
        if not jobs:
            return {"status": "no_jobs", "message": "No processing jobs found"}
        
        # Check if any job is completed
        completed_jobs = [job for job in jobs if job.get("status") == "completed"]
        failed_jobs = [job for job in jobs if job.get("status") == "failed"]
        running_jobs = [job for job in jobs if job.get("status") in ["pending", "running"]]
        
        if failed_jobs:
            return {"status": "failed", "message": f"Found {len(failed_jobs)} failed jobs"}
        
        if completed_jobs and not running_jobs:
            return {"status": "completed", "message": f"Found {len(completed_jobs)} completed jobs, no running jobs"}
        
        if running_jobs:
            return {"status": "running", "message": f"Found {len(running_jobs)} running jobs"}
        
        return {"status": "unknown", "message": "Unknown job status"}
    
    async def fix_stuck_documents(self, dry_run: bool = True) -> Dict[str, Any]:
        """Detect and fix stuck documents"""
        logger.info(f"🔍 Scanning for stuck documents (dry_run: {dry_run})")
        
        # Get all documents
        documents = await self.get_all_documents()
        if not documents:
            logger.warning("No documents found")
            return {"scanned": 0, "stuck": 0, "fixed": 0, "errors": 0}
        
        stuck_documents = []
        fixed_count = 0
        error_count = 0
        
        for document in documents:
            document_id = document.get("id")
            if not document_id:
                continue
            
            if self.is_document_stuck(document):
                logger.info(f"🔍 Found potentially stuck document: {document_id}")
                stuck_documents.append(document)
                
                # Get detailed processing status
                processing_status = await self.get_document_processing_status(document_id)
                analysis = self.analyze_processing_jobs(processing_status)
                
                logger.info(f"📊 Analysis for {document_id}: {analysis}")
                
                if analysis["status"] == "completed":
                    if not dry_run:
                        success = await self.update_document_status(document_id, "completed")
                        if success:
                            fixed_count += 1
                            logger.info(f"✅ Fixed stuck document {document_id} - marked as completed")
                        else:
                            error_count += 1
                            logger.error(f"❌ Failed to fix document {document_id}")
                    else:
                        logger.info(f"🔧 Would fix document {document_id} - mark as completed")
                        fixed_count += 1
                
                elif analysis["status"] == "failed":
                    if not dry_run:
                        success = await self.update_document_status(document_id, "failed")
                        if success:
                            fixed_count += 1
                            logger.info(f"✅ Fixed stuck document {document_id} - marked as failed")
                        else:
                            error_count += 1
                            logger.error(f"❌ Failed to fix document {document_id}")
                    else:
                        logger.info(f"🔧 Would fix document {document_id} - mark as failed")
                        fixed_count += 1
                
                elif analysis["status"] == "running":
                    logger.info(f"⏳ Document {document_id} is still running - leaving as is")
                
                else:
                    logger.warning(f"⚠️  Document {document_id} has unknown status: {analysis}")
        
        result = {
            "scanned": len(documents),
            "stuck": len(stuck_documents),
            "fixed": fixed_count,
            "errors": error_count,
            "dry_run": dry_run
        }
        
        logger.info(f"📊 Scan complete: {result}")
        return result

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix stuck documents in MEP AI NABOX")
    parser.add_argument("--real", action="store_true", help="Actually fix documents (default is dry run)")
    parser.add_argument("--max-time", type=int, default=30, help="Maximum processing time in minutes before considering stuck (default: 30)")
    
    args = parser.parse_args()
    
    fixer = StuckDocumentFixer()
    result = await fixer.fix_stuck_documents(dry_run=not args.real)
    
    print("\n" + "="*50)
    print("STUCK DOCUMENTS SCAN RESULTS")
    print("="*50)
    print(f"Documents scanned: {result['scanned']}")
    print(f"Potentially stuck: {result['stuck']}")
    print(f"Fixed/Would fix: {result['fixed']}")
    print(f"Errors: {result['errors']}")
    print(f"Mode: {'DRY RUN' if result['dry_run'] else 'REAL EXECUTION'}")
    print("="*50)
    
    if result['dry_run'] and result['fixed'] > 0:
        print("\n💡 To actually fix the documents, run with --real flag")
        print("   Example: python fix_stuck_documents.py --real")

if __name__ == "__main__":
    asyncio.run(main()) 