#!/usr/bin/env python3
"""
Status Worker for MEP AI NABOX
Continuously processes status updates from the Redis queue and updates the core processor
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
import yaml
from pathlib import Path

def load_config():
    """Load configuration from main.yaml and set environment variables"""
    try:
        config_path = Path(__file__).parent.parent / "config" / "main.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Set Redis environment variables
            redis_config = config.get('core', {}).get('storage', {}).get('redis', {})
            os.environ.setdefault('REDIS_HOST', redis_config.get('host', 'localhost'))
            os.environ.setdefault('REDIS_PORT', str(redis_config.get('port', 6379)))
            os.environ.setdefault('REDIS_PASSWORD', redis_config.get('password', 'redis_password'))
            
            # Set PostgreSQL environment variables
            postgres_config = config.get('core', {}).get('storage', {}).get('postgresql', {})
            os.environ.setdefault('POSTGRES_HOST', postgres_config.get('host', 'localhost'))
            os.environ.setdefault('POSTGRES_PORT', str(postgres_config.get('port', 5432)))
            os.environ.setdefault('POSTGRES_DB', postgres_config.get('database', 'mep_ainabox'))
            os.environ.setdefault('POSTGRES_USER', postgres_config.get('user', 'mep_user'))
            os.environ.setdefault('POSTGRES_PASSWORD', postgres_config.get('password', 'mep_password'))
            
            # Set Elasticsearch environment variables
            es_config = config.get('core', {}).get('storage', {}).get('elasticsearch', {})
            os.environ.setdefault('ELASTICSEARCH_HOST', es_config.get('host', 'localhost'))
            os.environ.setdefault('ELASTICSEARCH_PORT', str(es_config.get('port', 9200)))
            os.environ.setdefault('ELASTICSEARCH_USERNAME', es_config.get('username', 'elastic'))
            os.environ.setdefault('ELASTICSEARCH_PASSWORD', es_config.get('password', 'elastic_password'))
            
            # Set Qdrant environment variables
            qdrant_config = config.get('core', {}).get('storage', {}).get('qdrant', {})
            os.environ.setdefault('QDRANT_HOST', qdrant_config.get('host', 'localhost'))
            os.environ.setdefault('QDRANT_PORT', str(qdrant_config.get('port', 6333)))
            os.environ.setdefault('QDRANT_API_KEY', qdrant_config.get('api_key', 'qdrant_api_key'))
            
            # Set Neo4j environment variables
            neo4j_config = config.get('core', {}).get('storage', {}).get('neo4j', {})
            os.environ.setdefault('NEO4J_URI', neo4j_config.get('uri', 'bolt://localhost:7687'))
            os.environ.setdefault('NEO4J_USER', neo4j_config.get('user', 'neo4j'))
            os.environ.setdefault('NEO4J_PASSWORD', neo4j_config.get('password', 'neo4j_password'))
            
            # Set MinIO environment variables
            minio_config = config.get('core', {}).get('storage', {}).get('minio', {})
            os.environ.setdefault('MINIO_ENDPOINT', minio_config.get('endpoint', 'localhost:9000'))
            os.environ.setdefault('MINIO_ACCESS_KEY', minio_config.get('access_key', 'minio_access_key'))
            os.environ.setdefault('MINIO_SECRET_KEY', minio_config.get('secret_key', 'minio_secret_key'))
            os.environ.setdefault('MINIO_BUCKET_NAME', minio_config.get('bucket_name', 'documents'))
            os.environ.setdefault('MINIO_USE_SSL', str(minio_config.get('use_ssl', False)).lower())
            
            logger.info("✅ Configuration loaded and environment variables set")
        else:
            logger.warning("⚠️ Configuration file not found, using default values")
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")

# Load configuration at startup
load_config()

CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://localhost:8001")
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")

class StatusWorker:
    """Status worker that continuously processes status updates from the queue"""
    
    def __init__(self):
        self.core_processor_url = CORE_PROCESSOR_URL
        self.processing_pipeline_url = PROCESSING_PIPELINE_URL
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
    
    async def process_single_status_update(self) -> Optional[Dict[str, Any]]:
        """Process a single status update from the queue"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.processing_pipeline_url}/process-status-update",
                    timeout=30.0  # Longer timeout for status processing
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.warning("⏰ Status update processing timed out")
            return {"status": "timeout", "error": "Status update timeout"}
        except Exception as e:
            logger.error(f"❌ Error processing status update: {e}")
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
        logger.info(f"🔄 Starting status worker (poll interval: {poll_interval}s)")
        self.running = True
        self.start_time = datetime.now()
        
        while self.running:
            try:
                # Process a status update
                result = await self.process_single_status_update()
                
                if result:
                    status = result.get("status")
                    
                    if status == "processed":
                        self.processed_count += 1
                        document_id = result.get("document_id", "unknown")
                        logger.info(f"✅ Processed status update for document {document_id} (total: {self.processed_count})")
                    
                    elif status == "failed":
                        self.error_count += 1
                        document_id = result.get("document_id", "unknown")
                        error = result.get("error", "unknown error")
                        logger.error(f"❌ Failed to process status update for document {document_id}: {error}")
                    
                    elif status == "no_updates":
                        # No status updates in queue, wait a bit longer
                        await asyncio.sleep(poll_interval * 2)
                        continue
                    
                    elif status == "timeout":
                        self.error_count += 1
                        logger.warning(f"⏰ Status update processing timed out (errors: {self.error_count})")
                    
                    elif status == "error":
                        self.error_count += 1
                        error = result.get("error", "unknown error")
                        logger.error(f"❌ Status worker error: {error}")
                
                # Small delay between updates
                await asyncio.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal, stopping status worker...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in status worker loop: {e}")
                self.error_count += 1
                await asyncio.sleep(poll_interval)
        
        logger.info("🛑 Status worker stopped")
    
    def print_stats(self):
        """Print worker statistics"""
        if self.start_time:
            runtime = datetime.now() - self.start_time
            runtime_str = str(runtime).split('.')[0]  # Remove microseconds
            
            print("\n" + "="*60)
            print("STATUS WORKER STATISTICS")
            print("="*60)
            print(f"Runtime: {runtime_str}")
            print(f"Status Updates Processed: {self.processed_count}")
            print(f"Errors: {self.error_count}")
            print(f"Success Rate: {(self.processed_count / (self.processed_count + self.error_count) * 100):.1f}%" if (self.processed_count + self.error_count) > 0 else "N/A")
            print("="*60)
    
    async def run_with_stats(self, poll_interval: float = 1.0, stats_interval: int = 60):
        """Run worker with periodic statistics"""
        logger.info(f"📊 Starting status worker with stats every {stats_interval} seconds")
        
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
    logger.info(f"🛑 Received signal {signum}, stopping status worker...")
    sys.exit(0)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Status Worker for MEP AI NABOX")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Poll interval in seconds")
    parser.add_argument("--stats-interval", type=int, default=60, help="Statistics interval in seconds")
    parser.add_argument("--no-stats", action="store_true", help="Disable periodic statistics")
    parser.add_argument("--test", action="store_true", help="Test mode - process one status update and exit")
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    worker = StatusWorker()
    
    if args.test:
        logger.info("🧪 Test mode - processing one status update")
        result = await worker.process_single_status_update()
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