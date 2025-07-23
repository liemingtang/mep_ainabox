#!/usr/bin/env python3
"""
Database State Manager for MEP AI NABOX
Provides atomic status updates using database transactions
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncpg
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ProcessingState:
    """Processing state structure"""
    document_id: str
    job_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    current_step: str
    progress: int
    results: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None

class DatabaseStateManager:
    """Database-driven state manager with atomic transactions"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url
        self.pool = None
        
    async def connect(self, database_url: str):
        """Connect to database"""
        try:
            self.pool = await asyncpg.create_pool(database_url)
            logger.info("✅ Connected to database state manager")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.pool:
            await self.pool.close()
            logger.info("Database state manager disconnected")
    
    async def atomic_status_update(self, document_id: str, job_id: str, status: str, 
                                 results: Dict[str, Any] = None, error_message: str = None) -> bool:
        """Atomic status update using database transaction"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Update document status
                    await conn.execute("""
                        UPDATE documents 
                        SET processing_status = $1::character varying(50),
                            error_message = $2,
                            updated_at = $3,
                            processed_at = CASE WHEN $1 = 'completed' THEN $3 ELSE processed_at END
                        WHERE id = $4
                    """, status, error_message, datetime.utcnow(), document_id)
                    
                    # Update job status
                    await conn.execute("""
                        UPDATE processing_jobs 
                        SET status = $1::character varying(50),
                            result_data = $2,
                            error_message = $3,
                            completed_at = CASE WHEN $1 IN ('completed', 'failed') THEN $4 ELSE completed_at END,
                            updated_at = $4
                        WHERE id = $5
                    """, status, json.dumps(results or {}), error_message, datetime.utcnow(), job_id)
                    
                    # Insert processing results if completed
                    if status == 'completed' and results:
                        await conn.execute("""
                            INSERT INTO processing_results (document_id, job_id, results, created_at)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (document_id) DO UPDATE SET
                                results = $3,
                                updated_at = $4
                        """, document_id, job_id, json.dumps(results), datetime.utcnow())
                    
                    logger.info(f"✅ Atomic status update completed for document {document_id}: {status}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Atomic status update failed for document {document_id}: {e}")
            return False
    
    async def get_processing_state(self, document_id: str) -> Optional[ProcessingState]:
        """Get current processing state for a document"""
        try:
            async with self.pool.acquire() as conn:
                # Get document and job information
                row = await conn.fetchrow("""
                    SELECT 
                        d.id as document_id,
                        d.processing_status,
                        d.error_message as doc_error,
                        j.id as job_id,
                        j.status as job_status,
                        j.result_data,
                        j.error_message as job_error,
                        j.started_at,
                        j.completed_at,
                        j.updated_at
                    FROM documents d
                    LEFT JOIN processing_jobs j ON d.id = j.document_id
                    WHERE d.id = $1
                    ORDER BY j.created_at DESC
                    LIMIT 1
                """, document_id)
                
                if not row:
                    return None
                
                # Parse result data
                results = {}
                if row['result_data']:
                    try:
                        results = json.loads(row['result_data'])
                    except:
                        results = {}
                
                return ProcessingState(
                    document_id=row['document_id'],
                    job_id=row['job_id'],
                    status=row['processing_status'],
                    current_step=results.get('current_step', 'unknown'),
                    progress=results.get('progress', 0),
                    results=results,
                    error_message=row['doc_error'] or row['job_error'],
                    started_at=row['started_at'].isoformat() if row['started_at'] else None,
                    completed_at=row['completed_at'].isoformat() if row['completed_at'] else None,
                    updated_at=row['updated_at'].isoformat() if row['updated_at'] else None
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to get processing state for {document_id}: {e}")
            return None
    
    async def create_processing_job(self, document_id: str, job_type: str = "text_extraction") -> Optional[str]:
        """Create a new processing job with atomic transaction"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Create job
                    job_id = await conn.fetchval("""
                        INSERT INTO processing_jobs (document_id, job_type, status, created_at)
                        VALUES ($1, $2, 'pending', $3)
                        RETURNING id
                    """, document_id, job_type, datetime.utcnow())
                    
                    # Update document status
                    await conn.execute("""
                        UPDATE documents 
                        SET processing_status = 'processing',
                            updated_at = $1
                        WHERE id = $2
                    """, datetime.utcnow(), document_id)
                    
                    logger.info(f"✅ Created processing job {job_id} for document {document_id}")
                    return str(job_id)
                    
        except Exception as e:
            logger.error(f"❌ Failed to create processing job for {document_id}: {e}")
            return None
    
    async def update_job_progress(self, job_id: str, progress: int, current_step: str, 
                                results: Dict[str, Any] = None) -> bool:
        """Update job progress with atomic transaction"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Update job progress
                    await conn.execute("""
                        UPDATE processing_jobs 
                        SET result_data = $1,
                            updated_at = $2
                        WHERE id = $3
                    """, json.dumps(results or {}), datetime.utcnow(), job_id)
                    
                    logger.info(f"✅ Updated job progress for {job_id}: {progress}% - {current_step}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to update job progress for {job_id}: {e}")
            return False
    
    async def get_stuck_documents(self, max_processing_time_minutes: int = 30) -> list:
        """Get documents that might be stuck in processing"""
        try:
            async with self.pool.acquire() as conn:
                stuck_time = datetime.utcnow() - timedelta(minutes=max_processing_time_minutes)
                
                rows = await conn.fetch("""
                    SELECT 
                        d.id as document_id,
                        d.processing_status,
                        d.created_at,
                        j.id as job_id,
                        j.status as job_status,
                        j.started_at,
                        j.completed_at
                    FROM documents d
                    LEFT JOIN processing_jobs j ON d.id = j.document_id
                    WHERE d.processing_status = 'processing'
                    AND d.created_at < $1
                    ORDER BY d.created_at DESC
                """, stuck_time)
                
                stuck_documents = []
                for row in rows:
                    stuck_documents.append({
                        'document_id': row['document_id'],
                        'processing_status': row['processing_status'],
                        'created_at': row['created_at'].isoformat(),
                        'job_id': row['job_id'],
                        'job_status': row['job_status'],
                        'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                        'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None
                    })
                
                return stuck_documents
                
        except Exception as e:
            logger.error(f"❌ Failed to get stuck documents: {e}")
            return []
    
    async def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """Clean up old completed/failed jobs"""
        try:
            async with self.pool.acquire() as conn:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                result = await conn.execute("""
                    DELETE FROM processing_jobs 
                    WHERE status IN ('completed', 'failed')
                    AND updated_at < $1
                """, cutoff_date)
                
                deleted_count = int(result.split()[-1])
                logger.info(f"🧹 Cleaned up {deleted_count} old jobs")
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old jobs: {e}")
            return 0

# Global state manager instance
state_manager = DatabaseStateManager() 