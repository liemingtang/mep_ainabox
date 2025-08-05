#!/usr/bin/env python3
"""
Redis Queue Manager for MEP AI NABOX
Provides reliable message delivery and status updates
"""

import asyncio
import json
import logging
import os
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import redis
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from main.yaml and set environment variables"""
    print("🔧 LOAD_CONFIG: Starting configuration loading...")
    try:
        config_path = Path(__file__).parent.parent / "config" / "main.yaml"
        print(f"🔧 LOAD_CONFIG: Config path: {config_path}")
        logger.info(f"🔧 Loading configuration from: {config_path}")
        if config_path.exists():
            print("🔧 LOAD_CONFIG: Config file exists, loading...")
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Set Redis environment variables
            redis_config = config.get('core', {}).get('storage', {}).get('redis', {})
            print(f"🔧 LOAD_CONFIG: Redis config: {redis_config}")
            logger.info(f"🔧 Redis config from file: {redis_config}")
            
            redis_host = redis_config.get('host', 'localhost')
            redis_port = str(redis_config.get('port', 6379))
            redis_password = redis_config.get('password', 'redis_password')
            
            print(f"🔧 LOAD_CONFIG: Setting Redis env vars - host: {redis_host}, port: {redis_port}, password: {redis_password}")
            logger.info(f"🔧 Setting Redis env vars - host: {redis_host}, port: {redis_port}, password: {redis_password}")
            
            os.environ.setdefault('REDIS_HOST', redis_host)
            os.environ.setdefault('REDIS_PORT', redis_port)
            os.environ.setdefault('REDIS_PASSWORD', redis_password)
            
            print(f"🔧 LOAD_CONFIG: After setting env vars - REDIS_HOST: {os.getenv('REDIS_HOST')}, REDIS_PORT: {os.getenv('REDIS_PORT')}, REDIS_PASSWORD: {os.getenv('REDIS_PASSWORD')}")
            logger.info(f"🔧 After setting env vars - REDIS_HOST: {os.getenv('REDIS_HOST')}, REDIS_PORT: {os.getenv('REDIS_PORT')}, REDIS_PASSWORD: {os.getenv('REDIS_PASSWORD')}")
            
            print("🔧 LOAD_CONFIG: Configuration loaded successfully!")
            logger.info("✅ Configuration loaded and environment variables set")
        else:
            print("🔧 LOAD_CONFIG: Config file not found!")
            logger.warning("⚠️ Configuration file not found, using default values")
    except Exception as e:
        print(f"🔧 LOAD_CONFIG: Error loading configuration: {e}")
        logger.error(f"❌ Error loading configuration: {e}")
        import traceback
        print(f"🔧 LOAD_CONFIG: Traceback: {traceback.format_exc()}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

@dataclass
class ProcessingJob:
    """Processing job message structure"""
    document_id: str
    job_id: str
    file_path: str
    filename: str
    document_type: str
    created_at: str
    priority: int = 1

@dataclass
class StatusUpdate:
    """Status update message structure"""
    document_id: str
    job_id: str
    status: str  # 'completed', 'failed', 'processing'
    results: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: str = None

class RedisQueueManager:
    """Redis-based queue manager for reliable message delivery"""
    
    def __init__(self, redis_url: str = None):
        logger.info("🔧 Initializing RedisQueueManager...")
        if redis_url is None:
            # Use environment variables for host networking
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_password = os.getenv("REDIS_PASSWORD", "redis_password")
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
            logger.info(f"🔧 Redis URL: {redis_url}")
            logger.info(f"🔧 Environment - REDIS_HOST: {redis_host}, REDIS_PORT: {redis_port}, REDIS_PASSWORD: '{redis_password}'")
        self.redis_url = redis_url
        self.redis_client = None
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        # TEMPORARY: Hardcode the password to bypass config loading issue
        self.redis_password = "redis_password"
        logger.info(f"🔧 TEMPORARY: Using hardcoded Redis password: {self.redis_password}")
        # Ensure password is set correctly
        if not self.redis_password or self.redis_password == "":
            self.redis_password = "redis_password"
            logger.warning("⚠️ Redis password was empty, using default: redis_password")
        logger.info(f"🔧 Final Redis connection params - host: {self.redis_host}, port: {self.redis_port}, password: '{self.redis_password}'")
        self.processing_queue = "document_processing"
        self.status_queue = "status_updates"
        self.failed_queue = "failed_jobs"
        self.retry_queue = "retry_jobs"
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
    async def connect(self):
        """Connect to Redis"""
        try:
            logger.info(f"🔧 Attempting to connect to Redis with host: {self.redis_host}, port: {self.redis_port}, password: '{self.redis_password}'")
            print(f"🔧 CONNECT: Attempting to connect to Redis with host: {self.redis_host}, port: {self.redis_port}, password: '{self.redis_password}'")
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True
            )
            logger.info("🔧 Redis client created, attempting ping...")
            print("🔧 CONNECT: Redis client created, attempting ping...")
            # Use sync ping for sync Redis client
            result = self.redis_client.ping()
            logger.info(f"✅ Connected to Redis queue manager - ping result: {result}")
            print(f"🔧 CONNECT: ✅ Connected to Redis queue manager - ping result: {result}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            print(f"🔧 CONNECT: ❌ Failed to connect to Redis: {e}")
            logger.error(f"❌ Redis connection params - host: {self.redis_host}, port: {self.redis_port}, password: {self.redis_password}")
            print(f"🔧 CONNECT: ❌ Redis connection params - host: {self.redis_host}, port: {self.redis_port}, password: '{self.redis_password}'")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Disconnected from Redis queue manager")
    
    async def enqueue_processing_job(self, job: ProcessingJob) -> bool:
        """Enqueue a processing job"""
        try:
            job_data = asdict(job)
            
            # Add to processing queue with priority
            self.redis_client.zadd(
                self.processing_queue,
                {json.dumps(job_data): job.priority}
            )
            logger.info(f"📤 Enqueued processing job for document {job.document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue processing job: {e}")
            return False
    
    async def dequeue_processing_job(self, timeout: int = 5) -> Optional[ProcessingJob]:
        """Dequeue a processing job"""
        try:
            # Get job with highest priority (lowest score)
            result = self.redis_client.zpopmin(self.processing_queue, count=1)
            
            if not result:
                return None
            
            job_data = json.loads(result[0][0])
            return ProcessingJob(**job_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue processing job: {e}")
            return None
    
    async def enqueue_status_update(self, status_update: StatusUpdate) -> bool:
        """Enqueue a status update"""
        try:
            status_data = asdict(status_update)
            
            # Add to status queue
            self.redis_client.lpush(
                self.status_queue,
                json.dumps(status_data)
            )
            logger.info(f"📤 Enqueued status update for document {status_update.document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue status update: {e}")
            return False
    
    async def dequeue_status_update(self, timeout: int = 5) -> Optional[StatusUpdate]:
        """Dequeue a status update"""
        try:
            # Get status update from queue
            result = self.redis_client.brpop(self.status_queue, timeout=timeout)
            
            if not result:
                return None
            
            status_data = json.loads(result[1])
            return StatusUpdate(**status_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to dequeue status update: {e}")
            return None
    
    async def enqueue_failed_job(self, job: ProcessingJob, error: str, retry_count: int = 0) -> bool:
        """Enqueue a failed job for retry or permanent failure"""
        try:
            failed_job = {
                'job': asdict(job),
                'error': error,
                'retry_count': retry_count,
                'failed_at': datetime.utcnow().isoformat()
            }
            
            if retry_count < self.max_retries:
                # Schedule retry
                retry_time = datetime.utcnow() + timedelta(seconds=self.retry_delay * (retry_count + 1))
                self.redis_client.zadd(
                    self.retry_queue,
                    {json.dumps(failed_job): retry_time.timestamp()}
                )
                logger.info(f"📅 Scheduled retry {retry_count + 1} for document {job.document_id}")
            else:
                # Permanent failure
                self.redis_client.lpush(
                    self.failed_queue,
                    json.dumps(failed_job)
                )
                logger.error(f"❌ Permanent failure for document {job.document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue failed job: {e}")
            return False
    
    async def get_retry_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs ready for retry"""
        try:
            current_time = datetime.utcnow().timestamp()
            
            # Get jobs ready for retry
            ready_jobs = self.redis_client.zrangebyscore(
                self.retry_queue,
                0,
                current_time
            )
            
            # Remove from retry queue
            if ready_jobs:
                self.redis_client.zremrangebyscore(
                    self.retry_queue,
                    0,
                    current_time
                )
            
            return [json.loads(job) for job in ready_jobs]
            
        except Exception as e:
            logger.error(f"❌ Failed to get retry jobs: {e}")
            return []
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            stats = {
                'processing_queue_size': self.redis_client.zcard(self.processing_queue),
                'status_queue_size': self.redis_client.llen(self.status_queue),
                'retry_queue_size': self.redis_client.zcard(self.retry_queue),
                'failed_queue_size': self.redis_client.llen(self.failed_queue),
                'timestamp': datetime.utcnow().isoformat()
            }
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {}
    
    async def clear_queues(self):
        """Clear all queues (for testing/debugging)"""
        try:
            self.redis_client.delete(
                self.processing_queue,
                self.status_queue,
                self.retry_queue,
                self.failed_queue
            )
            logger.info("🧹 Cleared all queues")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear queues: {e}")

# Create queue manager instance AFTER configuration is loaded
def create_queue_manager():
    """Create and return a queue manager instance with proper configuration"""
    logger.info("🔧 Creating queue manager instance...")
    # Load configuration when creating the queue manager
    load_config()
    return RedisQueueManager()

# Global queue manager instance - created lazily when first accessed
_queue_manager_instance = None

def get_queue_manager():
    """Get the queue manager instance, creating it if necessary"""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        logger.info("🔧 Lazy initialization of queue manager...")
        _queue_manager_instance = create_queue_manager()
    return _queue_manager_instance

# For backward compatibility, create the instance immediately
queue_manager = get_queue_manager() 