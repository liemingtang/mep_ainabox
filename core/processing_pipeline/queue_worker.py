#!/usr/bin/env python3
"""
Queue Worker for MEP AI NABOX
Continuously processes jobs from the Redis queue
"""

import asyncio
import httpx
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
import os
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")

class QueueWorker:
    """Queue worker that continuously processes jobs"""
    
    def __init__(self):
        self.processing_pipeline_url = PROCESSING_PIPELINE_URL
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
    
    async def process_single_job(self) -> Optional[Dict[str, Any]]:
        """Process a single job from the queue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.processing_pipeline_url}/process-queue-worker",
                    timeout=60.0  # Longer timeout for processing
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.warning("⏰ Job processing timed out")
            return {"status": "timeout", "error": "Processing timeout"}
        except Exception as e:
            logger.error(f"❌ Error processing job: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.processing_pipeline_url}/queue/stats", timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"queue_stats": {}}
    
    async def worker_loop(self, poll_interval: float = 1.0):
        """Main worker loop"""
        logger.info(f"🔄 Starting queue worker (poll interval: {poll_interval}s)")
        self.running = True
        self.start_time = datetime.now()
        
        while self.running:
            try:
                # Process a job
                result = await self.process_single_job()
                
                if result:
                    status = result.get("status")
                    
                    if status == "processed":
                        self.processed_count += 1
                        document_id = result.get("document_id", "unknown")
                        logger.info(f"✅ Processed job for document {document_id} (total: {self.processed_count})")
                    
                    elif status == "failed":
                        self.error_count += 1
                        document_id = result.get("document_id", "unknown")
                        error = result.get("error", "unknown error")
                        logger.error(f"❌ Failed to process job for document {document_id}: {error}")
                    
                    elif status == "no_jobs":
                        # No jobs in queue, wait a bit longer
                        await asyncio.sleep(poll_interval * 2)
                        continue
                    
                    elif status == "timeout":
                        self.error_count += 1
                        logger.warning(f"⏰ Job processing timed out (errors: {self.error_count})")
                    
                    elif status == "error":
                        self.error_count += 1
                        error = result.get("error", "unknown error")
                        logger.error(f"❌ Worker error: {error}")
                
                # Small delay between jobs
                await asyncio.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal, stopping worker...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in worker loop: {e}")
                self.error_count += 1
                await asyncio.sleep(poll_interval)
        
        logger.info("🛑 Queue worker stopped")
    
    def print_stats(self):
        """Print worker statistics"""
        if self.start_time:
            runtime = datetime.now() - self.start_time
            runtime_str = str(runtime).split('.')[0]  # Remove microseconds
            
            print("\n" + "="*60)
            print("QUEUE WORKER STATISTICS")
            print("="*60)
            print(f"Runtime: {runtime_str}")
            print(f"Jobs Processed: {self.processed_count}")
            print(f"Errors: {self.error_count}")
            print(f"Success Rate: {(self.processed_count / (self.processed_count + self.error_count) * 100):.1f}%" if (self.processed_count + self.error_count) > 0 else "N/A")
            print("="*60)
    
    async def run_with_stats(self, poll_interval: float = 1.0, stats_interval: int = 60):
        """Run worker with periodic statistics"""
        logger.info(f"📊 Starting worker with stats every {stats_interval} seconds")
        
        # Start worker loop
        worker_task = asyncio.create_task(self.worker_loop(poll_interval))
        
        # Start stats loop
        stats_task = asyncio.create_task(self.stats_loop(stats_interval))
        
        try:
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [worker_task, stats_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
            worker_task.cancel()
            stats_task.cancel()
        
        # Print final stats
        self.print_stats()
    
    async def stats_loop(self, interval: int):
        """Periodic statistics loop"""
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if not self.running:
                    break
                
                # Get queue stats
                stats = await self.get_queue_stats()
                queue_stats = stats.get("queue_stats", {})
                
                # Print current stats
                runtime = datetime.now() - self.start_time
                runtime_str = str(runtime).split('.')[0]
                
                logger.info(f"📊 Stats - Runtime: {runtime_str}, Processed: {self.processed_count}, Errors: {self.error_count}")
                logger.info(f"📊 Queue - Processing: {queue_stats.get('processing_queue_size', 0)}, Status: {queue_stats.get('status_queue_size', 0)}, Retry: {queue_stats.get('retry_queue_size', 0)}")
                
            except Exception as e:
                logger.error(f"Error in stats loop: {e}")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info(f"🛑 Received signal {signum}, stopping worker...")
    sys.exit(0)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Queue Worker for MEP AI NABOX")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Poll interval in seconds")
    parser.add_argument("--stats-interval", type=int, default=60, help="Statistics interval in seconds")
    parser.add_argument("--no-stats", action="store_true", help="Disable periodic statistics")
    parser.add_argument("--test", action="store_true", help="Test mode - process one job and exit")
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    worker = QueueWorker()
    
    if args.test:
        logger.info("🧪 Test mode - processing one job")
        result = await worker.process_single_job()
        print(json.dumps(result, indent=2))
        return
    
    if args.no_stats:
        # Simple worker loop
        await worker.worker_loop(args.poll_interval)
    else:
        # Worker with statistics
        await worker.run_with_stats(args.poll_interval, args.stats_interval)

if __name__ == "__main__":
    asyncio.run(main()) 