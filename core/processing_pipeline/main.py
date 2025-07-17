from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
import json
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MDIS Processing Pipeline", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://storage-manager:8004")

# Request/Response models
class ProcessingRequest(BaseModel):
    document_id: str
    job_id: str

class ProcessingResponse(BaseModel):
    status: str
    job_id: str
    document_id: str
    message: str
    processing_steps: list

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    results: Dict[str, Any] = {}
    error_message: Optional[str] = None

# In-memory job tracking (in production, this would be in a database)
processing_jobs = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "processing-pipeline"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Processing Pipeline",
        "version": "1.0.0",
        "services": {
            "core-processor": CORE_PROCESSOR_URL,
            "storage-manager": STORAGE_MANAGER_URL
        }
    }

@app.post("/process")
async def process_document(request: ProcessingRequest):
    """Process a document through the pipeline"""
    try:
        logger.info(f"Starting processing for document {request.document_id}, job {request.job_id}")
        
        # Initialize job tracking
        job_id = request.job_id
        document_id = request.document_id
        
        processing_jobs[job_id] = {
            "job_id": job_id,
            "document_id": document_id,
            "status": "processing",
            "progress": 0,
            "current_step": "text_extraction",
            "started_at": datetime.utcnow(),
            "results": {},
            "error_message": None
        }
        
        # Update job status in core processor
        await update_job_status(job_id, "running", {"current_step": "text_extraction"})
        
        # Simulate processing steps
        processing_steps = [
            "text_extraction",
            "metadata_extraction", 
            "embedding_generation",
            "entity_extraction",
            "relationship_mapping"
        ]
        
        for i, step in enumerate(processing_steps):
            logger.info(f"Processing step {i+1}/{len(processing_steps)}: {step}")
            
            # Update progress
            progress = int((i + 1) / len(processing_steps) * 100)
            processing_jobs[job_id]["progress"] = progress
            processing_jobs[job_id]["current_step"] = step
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(1)  # Simulate processing time
            
            # Update job status
            await update_job_status(job_id, "running", {
                "current_step": step,
                "progress": progress
            })
        
        # Mark as completed
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["results"] = {
            "text_extracted": True,
            "metadata_extracted": True,
            "embeddings_generated": True,
            "entities_extracted": True,
            "relationships_mapped": True
        }
        
        # Update final status
        await update_job_status(job_id, "completed", processing_jobs[job_id]["results"])
        
        logger.info(f"Processing completed for document {document_id}, job {job_id}")
        
        return ProcessingResponse(
            status="processing",
            job_id=job_id,
            document_id=document_id,
            message="Document processing started successfully",
            processing_steps=processing_steps
        )
        
    except Exception as e:
        logger.error(f"Error processing document {request.document_id}: {e}")
        
        # Update job status to failed
        if request.job_id in processing_jobs:
            processing_jobs[request.job_id]["status"] = "failed"
            processing_jobs[request.job_id]["error_message"] = str(e)
            await update_job_status(request.job_id, "failed", {"error": str(e)})
        
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/status/{job_id}")
async def get_processing_status(job_id: str):
    """Get the status of a processing job"""
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        
        return JobStatusResponse(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            current_step=job.get("current_step"),
            results=job.get("results", {}),
            error_message=job.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")

async def update_job_status(job_id: str, status: str, result_data: Dict[str, Any] = None):
    """Update job status in the core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CORE_PROCESSOR_URL}/processing/jobs/{job_id}/status",
                json={
                    "status": status,
                    "result_data": result_data or {}
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Updated job {job_id} status to {status}")
    except Exception as e:
        logger.warning(f"Failed to update job status for {job_id}: {e}")

@app.get("/api/v1/process")
async def process_document_legacy():
    """Legacy endpoint for backward compatibility"""
    return await process_document(ProcessingRequest(
        document_id="legacy",
        job_id="legacy_job"
    ))

@app.get("/api/v1/status/{job_id}")
async def get_processing_status_legacy(job_id: str):
    """Legacy endpoint for backward compatibility"""
    return await get_processing_status(job_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 