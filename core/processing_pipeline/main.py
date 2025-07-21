from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import os
import json
import logging
import subprocess
import tempfile
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
EMBEDDING_PROCESSOR_URL = os.getenv("EMBEDDING_PROCESSOR_URL", "http://embedding-processor:8007")
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://storage-manager:8004")

# Embedding provider configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface")

# Dynamic text processor configuration
DYNAMIC_TEXT_PROCESSOR_SCRIPT = os.getenv("DYNAMIC_TEXT_PROCESSOR_SCRIPT", "/app/core/core/text_processor_dynamic.sh")

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

class DirectProcessingRequest(BaseModel):
    folder_path: str
    max_depth: Optional[int] = 0
    concurrent: Optional[int] = 5
    recursive: Optional[bool] = True

class DirectProcessingResponse(BaseModel):
    status: str
    job_id: str
    folder_path: str
    message: str
    files_processed: int
    files_failed: int
    total_files: int

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
            "embedding-processor": EMBEDDING_PROCESSOR_URL,
            "storage-manager": STORAGE_MANAGER_URL
        },
        "text_processing": "dynamic_text_processor"
    }

async def get_document_info(document_id: str) -> Dict[str, Any]:
    """Get document information from core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CORE_PROCESSOR_URL}/documents/{document_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get document info for {document_id}: {e}")
        raise

async def extract_text_from_document(document_id: str, file_path: str) -> Dict[str, Any]:
    """Extract text from document using dynamic text processor"""
    try:
        logger.info(f"Extracting text from document {document_id} at {file_path}")
        
        # Get the directory containing the file
        file_dir = os.path.dirname(file_path)
        if not file_dir:
            file_dir = "."
        
        # Run the dynamic text processor script
        cmd = [
            DYNAMIC_TEXT_PROCESSOR_SCRIPT,
            file_dir,
            "--max-depth", "0",  # Only process the immediate directory
            "--output", "json",
            "--concurrent", "1"   # Single file processing
        ]
        
        logger.info(f"Running dynamic text processor: {' '.join(cmd)}")
        
        # Execute the script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60.0,
            cwd="/app"  # Set working directory
        )
        
        if result.returncode != 0:
            logger.error(f"Dynamic text processor failed: {result.stderr}")
            raise Exception(f"Text extraction failed: {result.stderr}")
        
        # Parse the JSON output
        try:
            output_data = json.loads(result.stdout)
            
            # Find the specific file in the results
            file_name = os.path.basename(file_path)
            file_result = None
            
            for file_info in output_data.get("files", []):
                if file_info.get("filename") == file_name:
                    file_result = file_info
                    break
            
            if not file_result:
                raise Exception(f"File {file_name} not found in text processor results")
            
            # Format the result to match the expected structure
            result_data = {
                "document_id": document_id,
                "success": True,
                "text_content": file_result.get("text_content", ""),
                "text_length": file_result.get("text_length", 0),
                "quality_score": file_result.get("quality_score", 1.0),
                "extracted_tables": file_result.get("extracted_tables", []),
                "layout_info": file_result.get("layout_info", {}),
                "file_path": file_path
            }
            
            logger.info(f"Text extraction completed for document {document_id}")
            return result_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse text processor output: {e}")
            raise Exception(f"Invalid text processor output: {e}")
            
    except subprocess.TimeoutExpired:
        logger.error(f"Text extraction timed out for document {document_id}")
        raise Exception("Text extraction timed out")
    except Exception as e:
        logger.error(f"Text extraction failed for document {document_id}: {e}")
        raise

async def generate_embeddings(document_id: str, text_content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate embeddings using embedding processor"""
    try:
        logger.info(f"Generating embeddings for document {document_id}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EMBEDDING_PROCESSOR_URL}/process",
                json={
                    "document_id": document_id,
                    "text_content": text_content,
                    "metadata": metadata or {},
                    "provider": EMBEDDING_PROVIDER
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Embedding generation completed for document {document_id} using {EMBEDDING_PROVIDER}")
            return result
            
    except Exception as e:
        logger.error(f"Embedding generation failed for document {document_id}: {e}")
        raise

async def process_folder_directly(folder_path: str, max_depth: int = 0, concurrent: int = 5, recursive: bool = True) -> Dict[str, Any]:
    """Process a folder directly using dynamic text processor"""
    try:
        logger.info(f"Processing folder directly: {folder_path}")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job tracking
        processing_jobs[job_id] = {
            "job_id": job_id,
            "folder_path": folder_path,
            "status": "processing",
            "progress": 0,
            "current_step": "text_extraction",
            "started_at": datetime.utcnow(),
            "results": {},
            "error_message": None,
            "files_processed": 0,
            "files_failed": 0,
            "total_files": 0
        }
        
        # Run the text processor directly
        text_processor_script = "/app/core/core/processors/text_processor/text_processor.py"
        
        cmd = [
            "python", text_processor_script,
            folder_path,
            "--max-depth", str(max_depth),
            "--output", "json",
            "--concurrent", str(concurrent)
        ]
        
        if not recursive:
            cmd.append("--no-recursive")
        
        logger.info(f"Running text processor: {' '.join(cmd)}")
        
        # Execute the script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300.0,  # 5 minutes timeout
            cwd="/app"
        )
        
        # Log the output for debugging (truncated for logs)
        logger.info(f"Text processor stdout length: {len(result.stdout)}")
        logger.info(f"Text processor stderr length: {len(result.stderr)}")
        if result.stdout:
            logger.info(f"Text processor stdout preview: {result.stdout[:200]}...")
        if result.stderr:
            logger.info(f"Text processor stderr preview: {result.stderr[:200]}...")
        
        if result.returncode != 0:
            error_msg = f"Text processor failed: {result.stderr}"
            logger.error(error_msg)
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error_message"] = error_msg
            return {
                "status": "failed",
                "job_id": job_id,
                "error": error_msg
            }
        
        # Parse the JSON output
        try:
            output_data = json.loads(result.stdout)
            files = output_data.get("results", [])
            
            logger.info(f"Found {len(files)} files to process")
            
            # Update job with file count
            processing_jobs[job_id]["total_files"] = len(files)
            processing_jobs[job_id]["progress"] = 20
            
            # Process each file through the embedding pipeline
            processed_count = 0
            failed_count = 0
            
            for file_info in files:
                try:
                    # Generate document ID for this file
                    document_id = str(uuid.uuid4())
                    
                    # Extract text content
                    text_content = file_info.get("text_content", "")
                    if not text_content:
                        logger.warning(f"No text content for file: {file_info.get('file_path', 'unknown')}")
                        failed_count += 1
                        continue
                    
                    # Generate embeddings
                    metadata = {
                        "filename": os.path.basename(file_info.get("file_path", "")),
                        "file_path": file_info.get("file_path"),
                        "file_size": file_info.get("file_size"),
                        "text_length": file_info.get("text_length"),
                        "quality_score": file_info.get("quality_score"),
                        "folder_path": folder_path
                    }
                    
                    embedding_result = await generate_embeddings(document_id, text_content, metadata)
                    
                    if embedding_result.get("status") == "completed":
                        processed_count += 1
                        logger.info(f"Successfully processed file: {file_info.get('file_path')}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to generate embeddings for: {file_info.get('file_path')}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing file {file_info.get('file_path', 'unknown')}: {e}")
            
            # Update final job status
            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["progress"] = 100
            processing_jobs[job_id]["files_processed"] = processed_count
            processing_jobs[job_id]["files_failed"] = failed_count
            processing_jobs[job_id]["results"] = {
                "total_files": len(files),
                "processed_files": processed_count,
                "failed_files": failed_count,
                "folder_path": folder_path
            }
            
            logger.info(f"Folder processing completed. Processed: {processed_count}, Failed: {failed_count}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "folder_path": folder_path,
                "message": f"Successfully processed {processed_count} files",
                "files_processed": processed_count,
                "files_failed": failed_count,
                "total_files": len(files)
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse text processor output: {e}"
            logger.error(error_msg)
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error_message"] = error_msg
            return {
                "status": "failed",
                "job_id": job_id,
                "error": error_msg
            }
            
    except subprocess.TimeoutExpired:
        error_msg = f"Folder processing timed out for {folder_path}"
        logger.error(error_msg)
        if job_id in processing_jobs:
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error_message"] = error_msg
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Folder processing failed for {folder_path}: {e}"
        logger.error(error_msg)
        if job_id in processing_jobs:
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error_message"] = error_msg
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg
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
        
        # Step 1: Get document information
        logger.info(f"Step 1/3: Getting document information for {document_id}")
        document_info = await get_document_info(document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            raise Exception("Document file path not found")
        
        # Update progress
        processing_jobs[job_id]["progress"] = 20
        await update_job_status(job_id, "running", {
            "current_step": "text_extraction",
            "progress": 20
        })
        
        # Step 2: Extract text from document
        logger.info(f"Step 2/3: Extracting text from {file_path}")
        text_result = await extract_text_from_document(document_id, file_path)
        
        if not text_result.get("success"):
            raise Exception(f"Text extraction failed: {text_result.get('error', 'Unknown error')}")
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            raise Exception("No text content extracted from document")
        
        # Update progress
        processing_jobs[job_id]["progress"] = 60
        processing_jobs[job_id]["results"]["text_extracted"] = True
        processing_jobs[job_id]["results"]["text_content"] = text_content
        processing_jobs[job_id]["results"]["text_content_length"] = len(text_content)
        
        await update_job_status(job_id, "running", {
            "current_step": "embedding_generation",
            "progress": 60,
            "text_extracted": True,
            "text_content_length": len(text_content)
        })
        
        # Step 3: Generate embeddings
        logger.info(f"Step 3/3: Generating embeddings for {len(text_content)} characters of text")
        embedding_result = await generate_embeddings(
            document_id, 
            text_content, 
            metadata={
                "filename": document_info.get("filename"),
                "document_type": document_info.get("document_type"),
                "file_path": file_path
            }
        )
        
        if not embedding_result.get("success"):
            raise Exception(f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}")
        
        # Mark as completed
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["results"].update({
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": (datetime.utcnow() - processing_jobs[job_id]["started_at"]).total_seconds(),
            "embedding_result": embedding_result
        })
        
        # Update final status
        await update_job_status(job_id, "completed", processing_jobs[job_id]["results"])
        
        # Update document status to completed
        await update_document_status(document_id, "completed")
        
        logger.info(f"Processing completed for document {document_id}, job {job_id}")
        
        return ProcessingResponse(
            status="processing",
            job_id=job_id,
            document_id=document_id,
            message="Document processing started successfully",
            processing_steps=["text_extraction", "embedding_generation"]
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

@app.post("/jobs/{document_id}/status")
async def update_job_status_from_processor(document_id: str, status_update: dict):
    """Update job status from individual processors and handle document completion"""
    try:
        status = status_update.get("status")
        result_data = status_update.get("result_data", {})
        
        logger.info(f"Received job status update for document {document_id}: {status}")
        
        # Find the job for this document
        job_id = None
        for jid, job in processing_jobs.items():
            if job.get("document_id") == document_id:
                job_id = jid
                break
        
        if job_id:
            # Update the job status
            processing_jobs[job_id]["status"] = status
            if status == "completed":
                processing_jobs[job_id]["progress"] = 100
                processing_jobs[job_id]["results"] = result_data
            elif status == "failed":
                processing_jobs[job_id]["error_message"] = result_data.get("error", "Unknown error")
            
            # Update job status in core processor
            await update_job_status(job_id, status, result_data)
            
            # If job is completed, update document status
            if status == "completed":
                await update_document_status(document_id, "completed")
                logger.info(f"Document {document_id} processing completed")
            elif status == "failed":
                await update_document_status(document_id, "failed")
                logger.info(f"Document {document_id} processing failed")
        
        return {"message": "Job status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating job status for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating job status: {str(e)}")

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

async def update_document_status(document_id: str, status: str):
    """Update document status in the core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CORE_PROCESSOR_URL}/documents/{document_id}/status",
                json={
                    "processing_status": status
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Updated document {document_id} status to {status}")
    except Exception as e:
        logger.warning(f"Failed to update document status for {document_id}: {e}")

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

@app.post("/process-folder")
async def process_folder(request: DirectProcessingRequest):
    """Process a folder directly using dynamic text processor"""
    try:
        logger.info(f"Direct folder processing request: {request.folder_path}")
        
        # Validate folder path
        if not os.path.exists(request.folder_path):
            raise HTTPException(
                status_code=400,
                detail=f"Folder path does not exist: {request.folder_path}"
            )
        
        # Process the folder
        result = await process_folder_directly(
            folder_path=request.folder_path,
            max_depth=request.max_depth,
            concurrent=request.concurrent,
            recursive=request.recursive
        )
        
        if result["status"] == "completed":
            return DirectProcessingResponse(
                status="success",
                job_id=result["job_id"],
                folder_path=request.folder_path,
                message=f"Successfully processed {result['files_processed']} files",
                files_processed=result["files_processed"],
                files_failed=result["files_failed"],
                total_files=result["total_files"]
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error occurred")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in direct folder processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/folder-status/{job_id}")
async def get_folder_processing_status(job_id: str):
    """Get status of folder processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    job = processing_jobs[job_id]
    
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job.get("current_step"),
        "folder_path": job.get("folder_path"),
        "files_processed": job.get("files_processed", 0),
        "files_failed": job.get("files_failed", 0),
        "total_files": job.get("total_files", 0),
        "started_at": job.get("started_at"),
        "error_message": job.get("error_message"),
        "results": job.get("results", {})
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 