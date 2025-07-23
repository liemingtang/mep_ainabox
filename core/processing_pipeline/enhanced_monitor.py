#!/usr/bin/env python3
"""
Enhanced Monitor for MEP AI NABOX
Uses queue and state management systems for comprehensive monitoring
"""

import asyncio
import httpx
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CORE_PROCESSOR_URL = "http://localhost:8001"
PROCESSING_PIPELINE_URL = "http://localhost:8003"

class EnhancedMonitor:
    """Enhanced monitoring system using queue and state management"""
    
    def __init__(self):
        self.core_processor_url = CORE_PROCESSOR_URL
        self.processing_pipeline_url = PROCESSING_PIPELINE_URL
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.processing_pipeline_url}/queue/stats", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    async def get_stuck_documents_from_state(self) -> List[Dict[str, Any]]:
        """Get stuck documents using state manager"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.processing_pipeline_url}/state/stuck-documents", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("stuck_documents", [])
        except Exception as e:
            logger.error(f"Failed to get stuck documents from state: {e}")
            return []
    
    async def get_document_state(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document state using state manager"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.processing_pipeline_url}/state/{document_id}", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get document state for {document_id}: {e}")
            return None
    
    async def process_queue_worker(self) -> Dict[str, Any]:
        """Process a job from the queue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.processing_pipeline_url}/process-queue-worker", timeout=30.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to process queue worker: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_retry_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs ready for retry"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.processing_pipeline_url}/queue/retry-jobs", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("retry_jobs", [])
        except Exception as e:
            logger.error(f"Failed to get retry jobs: {e}")
            return []
    
    async def clear_queues(self) -> bool:
        """Clear all queues"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.processing_pipeline_url}/queue/clear", timeout=10.0)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to clear queues: {e}")
            return False
    
    async def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """Clean up old jobs"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.processing_pipeline_url}/state/cleanup?days_old={days_old}", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("deleted_count", 0)
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from core processor"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.core_processor_url}/documents", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []
    
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
                return True
        except Exception as e:
            logger.error(f"Failed to update document {document_id} status: {e}")
            return False
    
    async def analyze_and_fix_stuck_documents(self, dry_run: bool = True) -> Dict[str, Any]:
        """Analyze and fix stuck documents using enhanced monitoring"""
        logger.info(f"🔍 Enhanced analysis of stuck documents (dry_run: {dry_run})")
        
        results = {
            "queue_stats": {},
            "stuck_documents": [],
            "retry_jobs": [],
            "processed_jobs": 0,
            "fixed_documents": 0,
            "errors": 0,
            "dry_run": dry_run
        }
        
        # Get queue statistics
        queue_stats = await self.get_queue_stats()
        results["queue_stats"] = queue_stats.get("queue_stats", {})
        
        # Get stuck documents from state manager
        stuck_documents = await self.get_stuck_documents_from_state()
        results["stuck_documents"] = stuck_documents
        
        # Get retry jobs
        retry_jobs = await self.get_retry_jobs()
        results["retry_jobs"] = retry_jobs
        
        logger.info(f"📊 Queue Stats: {results['queue_stats']}")
        logger.info(f"📊 Found {len(stuck_documents)} potentially stuck documents")
        logger.info(f"📊 Found {len(retry_jobs)} retry jobs")
        
        # Process queue worker if there are jobs
        if results["queue_stats"].get("processing_queue_size", 0) > 0:
            logger.info("🔄 Processing queue worker...")
            worker_result = await self.process_queue_worker()
            if worker_result.get("status") == "processed":
                results["processed_jobs"] += 1
                logger.info(f"✅ Processed job for document {worker_result.get('document_id')}")
            elif worker_result.get("status") == "failed":
                results["errors"] += 1
                logger.error(f"❌ Failed to process job: {worker_result.get('error')}")
        
        # Analyze stuck documents
        for doc in stuck_documents:
            document_id = doc.get("document_id")
            logger.info(f"🔍 Analyzing stuck document: {document_id}")
            
            # Get detailed state
            state = await self.get_document_state(document_id)
            if not state:
                continue
            
            # Analyze based on state
            if state.get("status") == "processing":
                # Check if job is actually completed
                job_status = state.get("job_status")
                if job_status == "completed":
                    if not dry_run:
                        success = await self.update_document_status(document_id, "completed")
                        if success:
                            results["fixed_documents"] += 1
                            logger.info(f"✅ Fixed stuck document {document_id} - marked as completed")
                        else:
                            results["errors"] += 1
                            logger.error(f"❌ Failed to fix document {document_id}")
                    else:
                        logger.info(f"🔧 Would fix document {document_id} - mark as completed")
                        results["fixed_documents"] += 1
                
                elif job_status == "failed":
                    if not dry_run:
                        success = await self.update_document_status(document_id, "failed")
                        if success:
                            results["fixed_documents"] += 1
                            logger.info(f"✅ Fixed stuck document {document_id} - marked as failed")
                        else:
                            results["errors"] += 1
                            logger.error(f"❌ Failed to fix document {document_id}")
                    else:
                        logger.info(f"🔧 Would fix document {document_id} - mark as failed")
                        results["fixed_documents"] += 1
        
        return results
    
    async def run_continuous_monitoring(self, interval_seconds: int = 60, max_iterations: int = None):
        """Run continuous monitoring"""
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval_seconds}s)")
        
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            try:
                logger.info(f"📊 Monitoring iteration {iteration + 1}")
                
                # Run analysis
                results = await self.analyze_and_fix_stuck_documents(dry_run=False)
                
                # Log summary
                logger.info(f"📊 Iteration {iteration + 1} Summary:")
                logger.info(f"   - Queue size: {results['queue_stats'].get('processing_queue_size', 0)}")
                logger.info(f"   - Stuck documents: {len(results['stuck_documents'])}")
                logger.info(f"   - Retry jobs: {len(results['retry_jobs'])}")
                logger.info(f"   - Processed jobs: {results['processed_jobs']}")
                logger.info(f"   - Fixed documents: {results['fixed_documents']}")
                logger.info(f"   - Errors: {results['errors']}")
                
                # Wait for next iteration
                if max_iterations is None or iteration + 1 < max_iterations:
                    logger.info(f"⏳ Waiting {interval_seconds} seconds for next iteration...")
                    await asyncio.sleep(interval_seconds)
                
                iteration += 1
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring iteration {iteration + 1}: {e}")
                await asyncio.sleep(interval_seconds)
                iteration += 1
        
        logger.info("🛑 Continuous monitoring stopped")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Enhanced Monitor for MEP AI NABOX")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--continuous", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")
    parser.add_argument("--iterations", type=int, default=None, help="Number of iterations for continuous monitoring")
    parser.add_argument("--clear-queues", action="store_true", help="Clear all queues")
    parser.add_argument("--cleanup", type=int, help="Clean up jobs older than N days")
    parser.add_argument("--queue-stats", action="store_true", help="Show queue statistics only")
    
    args = parser.parse_args()
    
    monitor = EnhancedMonitor()
    
    if args.clear_queues:
        logger.info("🧹 Clearing all queues...")
        success = await monitor.clear_queues()
        if success:
            logger.info("✅ Queues cleared successfully")
        else:
            logger.error("❌ Failed to clear queues")
        return
    
    if args.cleanup:
        logger.info(f"🧹 Cleaning up jobs older than {args.cleanup} days...")
        deleted_count = await monitor.cleanup_old_jobs(args.cleanup)
        logger.info(f"✅ Cleaned up {deleted_count} old jobs")
        return
    
    if args.queue_stats:
        logger.info("📊 Getting queue statistics...")
        stats = await monitor.get_queue_stats()
        print(json.dumps(stats, indent=2))
        return
    
    if args.continuous:
        await monitor.run_continuous_monitoring(args.interval, args.iterations)
    else:
        # Single analysis run
        results = await monitor.analyze_and_fix_stuck_documents(dry_run=args.dry_run)
        
        print("\n" + "="*60)
        print("ENHANCED MONITORING RESULTS")
        print("="*60)
        print(f"Queue Statistics:")
        for key, value in results["queue_stats"].items():
            print(f"  {key}: {value}")
        print(f"Stuck Documents: {len(results['stuck_documents'])}")
        print(f"Retry Jobs: {len(results['retry_jobs'])}")
        print(f"Processed Jobs: {results['processed_jobs']}")
        print(f"Fixed Documents: {results['fixed_documents']}")
        print(f"Errors: {results['errors']}")
        print(f"Mode: {'DRY RUN' if results['dry_run'] else 'REAL EXECUTION'}")
        print("="*60)
        
        if results['dry_run'] and results['fixed_documents'] > 0:
            print("\n💡 To actually fix the documents, run without --dry-run flag")
            print("   Example: python enhanced_monitor.py")

if __name__ == "__main__":
    asyncio.run(main()) 