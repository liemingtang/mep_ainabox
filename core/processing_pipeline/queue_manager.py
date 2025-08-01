#!/usr/bin/env python3
"""
Redis Queue Manager for MEP AI NABOX
Provides reliable message delivery and status updates
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

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
        if redis_url is None:
            # Use environment variables for host networking
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_password = os.getenv("REDIS_PASSWORD", "redis_password")
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
        self.redis_url = redis_url
        self.redis_client = None
        self.processing_queue = "document_processing"
        self.status_queue = "status_updates"
        self.failed_queue = "failed_jobs"
        self.retry_queue = "retry_jobs"
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis queue manager")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis queue manager")
    
    async def enqueue_processing_job(self, job: ProcessingJob) -> bool:
        """Enqueue a processing job"""
        try:
            job_data = asdict(job)
            # Don't add timestamp to job_data since it's not in the ProcessingJob dataclass
            
            # Add to processing queue with priority
            await self.redis_client.zadd(
                self.processing_queue,
                {json.dumps(job_data): job.priority}
            )
            
            logger.info(f"✅ Enqueued processing job for document {job.document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue processing job: {e}")
            return False
    
    async def dequeue_processing_job(self, timeout: int = 5) -> Optional[ProcessingJob]:
        """Dequeue a processing job with timeout"""
        try:
            # Get job with highest priority (lowest score)
            result = await self.redis_client.zpopmin(self.processing_queue, count=1)
            
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
            status_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Add to status queue
            await self.redis_client.lpush(
                self.status_queue,
                json.dumps(status_data)
            )
            
            logger.info(f"✅ Enqueued status update for document {status_update.document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue status update: {e}")
            return False
    
    async def dequeue_status_update(self, timeout: int = 5) -> Optional[StatusUpdate]:
        """Dequeue a status update with timeout"""
        try:
            # Get status update from queue
            result = await self.redis_client.brpop(self.status_queue, timeout=timeout)
            
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
                await self.redis_client.zadd(
                    self.retry_queue,
                    {json.dumps(failed_job): retry_time.timestamp()}
                )
                logger.info(f"📅 Scheduled retry {retry_count + 1} for document {job.document_id}")
            else:
                # Permanent failure
                await self.redis_client.lpush(
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
            ready_jobs = await self.redis_client.zrangebyscore(
                self.retry_queue,
                0,
                current_time
            )
            
            # Remove from retry queue
            if ready_jobs:
                await self.redis_client.zremrangebyscore(
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
                'processing_queue_size': await self.redis_client.zcard(self.processing_queue),
                'status_queue_size': await self.redis_client.llen(self.status_queue),
                'retry_queue_size': await self.redis_client.zcard(self.retry_queue),
                'failed_queue_size': await self.redis_client.llen(self.failed_queue),
                'timestamp': datetime.utcnow().isoformat()
            }
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {}
    
    async def clear_queues(self):
        """Clear all queues (for testing/debugging)"""
        try:
            await self.redis_client.delete(
                self.processing_queue,
                self.status_queue,
                self.retry_queue,
                self.failed_queue
            )
            logger.info("🧹 Cleared all queues")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear queues: {e}")

# Global queue manager instance
queue_manager = RedisQueueManager() 