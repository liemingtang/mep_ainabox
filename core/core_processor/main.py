#!/usr/bin/env python3
"""
Core Processor - Main Document Processing Orchestrator
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.database import init_database
from app.logging import setup_logging
from app.models.document import DocumentMetadata, ProcessingJob
from app.services.document_service import DocumentService
from app.services.processing_service import ProcessingService
from app.services.storage_service import StorageService

# Setup logging
logger = setup_logging()

# Prometheus metrics - using singleton pattern to avoid duplicate registration
class Metrics:
    _instance = None
    _metrics = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Metrics, cls).__new__(cls)
            cls._instance._metrics = None
        return cls._instance
    
    def get_metrics(self):
        if self._metrics is None:
            self._metrics = {
                'request_count': Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status']),
                'request_latency': Histogram('http_request_duration_seconds', 'HTTP request latency')
            }
        return self._metrics

metrics_manager = Metrics()

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = asyncio.get_event_loop().time()
        
        response = await call_next(request)
        
        duration = asyncio.get_event_loop().time() - start_time
        metrics_instance = metrics_manager.get_metrics()
        metrics_instance['request_count'].labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        metrics_instance['request_latency'].observe(duration)
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Core Processor service...")
    
    # Initialize database connections
    await init_database()
    
    # Initialize services
    app.state.document_service = DocumentService()
    app.state.processing_service = ProcessingService(document_service=app.state.document_service)
    app.state.storage_service = StorageService()
    
    logger.info("Core Processor service started successfully")
    
    yield
    
    logger.info("Shutting down Core Processor service...")

# Create FastAPI application
app = FastAPI(
    title="Core Processor",
    description="Main document processing orchestrator for MDIS",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.core.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connections
        await app.state.storage_service.health_check()
        return {"status": "healthy", "service": "core-processor"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/documents/upload")
async def upload_document(document: DocumentMetadata):
    """Upload and process a new document"""
    try:
        logger.info(f"Processing document upload: {document.filename}")
        
        # Store document metadata
        doc_id = await app.state.document_service.create_document(document)
        
        # Route document for processing
        processing_job = await app.state.processing_service.route_document(doc_id, document)
        
        return {
            "document_id": doc_id,
            "processing_job_id": processing_job.id,
            "status": "processing",
            "message": "Document uploaded and processing started"
        }
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}"
        )

@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document information"""
    try:
        from uuid import UUID
        doc_uuid = UUID(document_id)
        document = await app.state.document_service.get_document(doc_uuid)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )

@app.get("/documents/{document_id}/processing-status")
async def get_processing_status(document_id: str):
    """Get document processing status"""
    try:
        from uuid import UUID
        doc_uuid = UUID(document_id)
        status_info = await app.state.processing_service.get_processing_status(doc_uuid)
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing status for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing status: {str(e)}"
        )

@app.post("/documents/{document_id}/reprocess")
async def reprocess_document(document_id: str):
    """Reprocess a document"""
    try:
        from uuid import UUID
        doc_uuid = UUID(document_id)
        processing_job = await app.state.processing_service.reprocess_document(doc_uuid)
        return {
            "document_id": document_id,
            "processing_job_id": processing_job.id,
            "status": "processing",
            "message": "Document reprocessing started"
        }
    except Exception as e:
        logger.error(f"Document reprocessing failed for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document reprocessing failed: {str(e)}"
        )

@app.get("/processing/jobs/{job_id}")
async def get_processing_job(job_id: str):
    """Get processing job information"""
    try:
        from uuid import UUID
        job_uuid = UUID(job_id)
        job = await app.state.processing_service.get_processing_job(job_uuid)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing job: {str(e)}"
        )

@app.post("/processing/jobs/{job_id}/status")
async def update_job_status(job_id: str, status_update: dict):
    """Update processing job status"""
    try:
        from uuid import UUID
        from app.models.document import JobStatus
        
        job_uuid = UUID(job_id)
        status_str = status_update.get("status")
        result_data = status_update.get("result_data", {})
        
        # Convert status string to JobStatus enum
        if status_str == "pending":
            job_status = JobStatus.PENDING
        elif status_str == "running":
            job_status = JobStatus.RUNNING
        elif status_str == "completed":
            job_status = JobStatus.COMPLETED
        elif status_str == "failed":
            job_status = JobStatus.FAILED
        elif status_str == "cancelled":
            job_status = JobStatus.CANCELLED
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_str}"
            )
        
        success = await app.state.processing_service.update_job_status(
            job_uuid, 
            job_status, 
            result_data
        )
        
        if success:
            return {"message": "Job status updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job status: {str(e)}"
        )

@app.post("/documents/{document_id}/status")
async def update_document_status_endpoint(document_id: str, status_update: dict):
    """Update document processing status"""
    try:
        from uuid import UUID
        from app.models.document import ProcessingStatus
        
        doc_uuid = UUID(document_id)
        status_str = status_update.get("processing_status")
        
        # Convert status string to ProcessingStatus enum
        try:
            doc_status = ProcessingStatus(status_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_str}"
            )
        
        success = await app.state.document_service.update_document_status(doc_uuid, doc_status)
        
        if success:
            return {"message": "Document status updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document status for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document status: {str(e)}"
        )

@app.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    document_type: str = None
):
    """List documents with optional filtering"""
    try:
        documents = await app.state.document_service.list_documents(
            skip=skip,
            limit=limit,
            status=status_filter,
            document_type=document_type
        )
        return documents
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all associated data"""
    try:
        from uuid import UUID
        doc_uuid = UUID(document_id)
        await app.state.document_service.delete_document(doc_uuid)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )

@app.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        stats = await app.state.document_service.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}"
        )

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("CORE_PROCESSOR_PORT", 8001))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting Core Processor on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=settings.system.debug,
        log_level=settings.core.logging.level.lower()
    ) 