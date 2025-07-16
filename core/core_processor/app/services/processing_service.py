"""
Processing service for managing document processing jobs and workflow
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

import asyncpg
import httpx

from app.database import get_postgres_pool
from app.logging import LoggerMixin
from app.models.document import (
    DocumentMetadata, ProcessingJob, ProcessingStep, JobStatus, ProcessingStatus
)


class ProcessingService(LoggerMixin):
    """Service for managing document processing jobs and workflow"""
    
    def __init__(self):
        self.postgres_pool = get_postgres_pool()
        self.processing_pipeline_url = "http://processing-pipeline:8003"
        self.document_router_url = "http://document-router:8002"
    
    async def route_document(self, document_id: UUID, document: DocumentMetadata) -> ProcessingJob:
        """Route document for processing"""
        try:
            self.logger.info(f"Routing document for processing: {document_id}")
            
            # Create processing job
            processing_job = await self._create_processing_job(document_id, ProcessingStep.TEXT_EXTRACTION)
            
            # Send to document router for analysis
            await self._send_to_document_router(document_id, document)
            
            # Send to processing pipeline
            await self._send_to_processing_pipeline(document_id, processing_job.id)
            
            # Update document status
            await self._update_document_status(document_id, ProcessingStatus.PROCESSING)
            
            self.logger.info(f"Document routed successfully: {document_id}")
            return processing_job
            
        except Exception as e:
            self.logger.error(f"Failed to route document {document_id}: {e}")
            await self._update_document_status(document_id, ProcessingStatus.FAILED, str(e))
            raise
    
    async def get_processing_status(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """Get processing status for a document"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Get document status
                doc_row = await conn.fetchrow(
                    "SELECT processing_status, error_message FROM documents WHERE id = $1",
                    str(document_id)
                )
                
                if not doc_row:
                    return None
                
                # Get processing jobs
                job_rows = await conn.fetch(
                    "SELECT * FROM processing_jobs WHERE document_id = $1 ORDER BY created_at",
                    str(document_id)
                )
                
                jobs = []
                for row in job_rows:
                    jobs.append({
                        "id": str(row['id']),
                        "job_type": row['job_type'],
                        "status": row['status'],
                        "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                        "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None,
                        "error_message": row['error_message'],
                        "retry_count": row['retry_count']
                    })
                
                return {
                    "document_id": str(document_id),
                    "processing_status": doc_row['processing_status'],
                    "error_message": doc_row['error_message'],
                    "processing_jobs": jobs
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get processing status for {document_id}: {e}")
            raise
    
    async def get_processing_job(self, job_id: UUID) -> Optional[ProcessingJob]:
        """Get processing job by ID"""
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM processing_jobs WHERE id = $1",
                    str(job_id)
                )
                
                if row:
                    # Convert JSONB fields back to dicts
                    row_dict = dict(row)
                    if isinstance(row_dict.get('result_data'), str):
                        row_dict['result_data'] = json.loads(row_dict['result_data'])
                    return ProcessingJob(**row_dict)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get processing job {job_id}: {e}")
            raise
    
    async def reprocess_document(self, document_id: UUID) -> ProcessingJob:
        """Reprocess a document"""
        try:
            self.logger.info(f"Reprocessing document: {document_id}")
            
            # Reset document status
            await self._update_document_status(document_id, ProcessingStatus.PENDING)
            
            # Cancel existing jobs
            await self._cancel_existing_jobs(document_id)
            
            # Create new processing job
            processing_job = await self._create_processing_job(document_id, ProcessingStep.TEXT_EXTRACTION)
            
            # Send to processing pipeline
            await self._send_to_processing_pipeline(document_id, processing_job.id)
            
            self.logger.info(f"Document reprocessing started: {document_id}")
            return processing_job
            
        except Exception as e:
            self.logger.error(f"Failed to reprocess document {document_id}: {e}")
            raise
    
    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update processing job status"""
        try:
            async with self.postgres_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE processing_jobs 
                    SET status = $1, 
                        result_data = $2, 
                        error_message = $3,
                        started_at = CASE WHEN $1 = 'running' AND started_at IS NULL THEN $4 ELSE started_at END,
                        completed_at = CASE WHEN $1 IN ('completed', 'failed', 'cancelled') THEN $4 ELSE completed_at END
                    WHERE id = $5
                    """,
                    status.value,
                    json.dumps(result_data) if result_data else '{}',
                    error_message,
                    datetime.utcnow(),
                    str(job_id)
                )
                
                return result.split()[-1] == "1"
                
        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")
            raise
    
    async def create_next_job(self, document_id: UUID, current_step: ProcessingStep) -> Optional[ProcessingJob]:
        """Create next processing job in the pipeline"""
        try:
            next_step = self._get_next_step(current_step)
            if next_step:
                return await self._create_processing_job(document_id, next_step)
            else:
                # All steps completed
                await self._update_document_status(document_id, ProcessingStatus.COMPLETED)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create next job: {e}")
            raise
    
    async def _create_processing_job(self, document_id: UUID, job_type: ProcessingStep) -> ProcessingJob:
        """Create a new processing job"""
        job = ProcessingJob(
            document_id=document_id,
            job_type=job_type
        )
        
        async with self.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO processing_jobs (
                    id, document_id, job_type, status, retry_count, max_retries, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                str(job.id),
                str(job.document_id),
                job.job_type.value,
                job.status.value,
                job.retry_count,
                job.max_retries,
                job.created_at
            )
            
            # Convert JSONB fields back to dicts
            row_dict = dict(row)
            if isinstance(row_dict.get('result_data'), str):
                row_dict['result_data'] = json.loads(row_dict['result_data'])
            return ProcessingJob(**row_dict)
    
    async def _send_to_document_router(self, document_id: UUID, document: DocumentMetadata):
        """Send document to document router for analysis"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.document_router_url}/analyze",
                    json={
                        "document_id": str(document_id),
                        "document": document.model_dump()
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
        except Exception as e:
            self.logger.warning(f"Failed to send to document router: {e}")
    
    async def _send_to_processing_pipeline(self, document_id: UUID, job_id: UUID):
        """Send document to processing pipeline"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.processing_pipeline_url}/process",
                    json={
                        "document_id": str(document_id),
                        "job_id": str(job_id)
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                
        except Exception as e:
            self.logger.error(f"Failed to send to processing pipeline: {e}")
            raise
    
    async def _update_document_status(
        self,
        document_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ):
        """Update document processing status"""
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE documents 
                    SET processing_status = $1, 
                        error_message = $2, 
                        updated_at = $3,
                        processed_at = CASE WHEN $1 = 'completed' THEN $3 ELSE processed_at END
                    WHERE id = $4
                    """,
                    status.value,
                    error_message,
                    datetime.utcnow(),
                    str(document_id)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update document status: {e}")
            raise
    
    async def _cancel_existing_jobs(self, document_id: UUID):
        """Cancel existing processing jobs for a document"""
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE processing_jobs 
                    SET status = 'cancelled', completed_at = $1
                    WHERE document_id = $2 AND status IN ('pending', 'running')
                    """,
                    datetime.utcnow(),
                    str(document_id)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to cancel existing jobs: {e}")
            raise
    
    def _get_next_step(self, current_step: ProcessingStep) -> Optional[ProcessingStep]:
        """Get the next processing step in the pipeline"""
        step_order = [
            ProcessingStep.TEXT_EXTRACTION,
            ProcessingStep.METADATA_EXTRACTION,
            ProcessingStep.EMBEDDING_GENERATION,
            ProcessingStep.ENTITY_EXTRACTION,
            ProcessingStep.RELATIONSHIP_MAPPING,
            ProcessingStep.CLIMATE_ANALYSIS,
            ProcessingStep.FINANCIAL_ANALYSIS,
            ProcessingStep.LEGAL_ANALYSIS
        ]
        
        try:
            current_index = step_order.index(current_step)
            if current_index + 1 < len(step_order):
                return step_order[current_index + 1]
            return None
        except ValueError:
            return None 