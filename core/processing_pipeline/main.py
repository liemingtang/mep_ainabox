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
import asyncio
from queue_manager import queue_manager, ProcessingJob, StatusUpdate
from state_manager import state_manager

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
    """Extract text from document using text processor service"""
    try:
        logger.info(f"=== EXTRACT_TEXT_FUNCTION_CALLED ===")
        logger.info(f"Extracting text from document {document_id} at {file_path}")
        
        # Check if this is a dynamically mounted file (from scan_folder)
        if '/app/scan_folder' in file_path:
            logger.info(f"Detected dynamically mounted file, using dynamic text processor for {file_path}")
            
            # Use dynamic text processor for files in dynamically mounted folders
            # Create a temporary container to extract text from the file
            container_name = f"mep-dynamic-text-extractor-{document_id[:8]}"
            
            # Convert container path to host path
            # The file path is /app/scan_folder/filename, which corresponds to /media/lie/DATA2/ai_scan_folder/filename
            host_file_path = file_path.replace('/app/scan_folder', '/media/lie/DATA2/ai_scan_folder')
            
            # Build the Docker command to run text extraction
            # Extract the directory and filename from the host file path
            import os
            file_dir = os.path.dirname(host_file_path)
            file_name = os.path.basename(host_file_path)
            
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "--network", "host",
                "-v", f"{file_dir}:/app/input_dir:ro",
                "mep-file-watcher:latest",
                "python3", "-c",
                f"""
import sys
import os
sys.path.append('/app')
sys.path.append('/app/core')

# Simple text extraction function
def extract_text_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {{
            "success": True,
            "text_content": content,
            "text_length": len(content),
            "quality_score": min(1.0, len(content) / 1000.0),
            "file_path": str(file_path)
        }}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e),
            "file_path": str(file_path)
        }}

file_path = '/app/input_dir/{file_name}'
result = extract_text_from_file(file_path)
import json
print(json.dumps(result))
"""
            ]
            
            logger.info(f"Running dynamic text extraction: {' '.join(docker_cmd)}")
            
            # Execute the Docker command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=60.0
            )
            
            if result.returncode != 0:
                logger.error(f"Dynamic text extraction failed: {result.stderr}")
                raise Exception(f"Dynamic text extraction failed: {result.stderr}")
            
            # Parse the JSON result
            try:
                extraction_result = json.loads(result.stdout.strip())
                logger.info(f"Dynamic text extraction completed for document {document_id}")
                logger.info(f"Text content length: {len(extraction_result.get('text_content', ''))}")
                return extraction_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse dynamic text extraction result: {e}")
                logger.error(f"Raw output: {result.stdout}")
                raise Exception(f"Failed to parse dynamic text extraction result: {e}")
        
        else:
            # Use the regular text processor service for files in standard locations
            text_processor_url = "http://text-processor:8005"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{text_processor_url}/extract-text",
                    json={
                        "document_path": file_path,
                        "document_id": document_id
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Text extraction completed for document {document_id}")
                logger.info(f"Text extraction result: {result}")
                logger.info(f"Text content length: {len(result.get('text_content', ''))}")
                return result
            
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
            logger.info(f"Embedding result: {result}")
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
    """Process a document through the pipeline with centralized status management"""
    try:
        logger.info(f"Starting processing for document {request.document_id}, job {request.job_id}")
        
        # Initialize job tracking locally (no external status updates during processing)
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
        
        # Step 1: Get document information
        logger.info(f"Step 1/3: Getting document information for {document_id}")
        document_info = await get_document_info(document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            raise Exception("Document file path not found")
        
        # Step 2: Extract text from document
        logger.info(f"Step 2/3: Extracting text from {file_path}")
        text_result = await extract_text_from_document(document_id, file_path)
        
        if not text_result.get("success"):
            raise Exception(f"Text extraction failed: {text_result.get('error', 'Unknown error')}")
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            raise Exception("No text content extracted from document")
        
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
        
        if embedding_result.get("status") != "completed":
            raise Exception(f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}")
        
        # Prepare final results
        final_results = {
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": (datetime.utcnow() - processing_jobs[job_id]["started_at"]).total_seconds(),
            "embedding_result": embedding_result,
            "text_extracted": True,
            "text_content_length": len(text_content)
        }
        
        # Update local job status
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["results"] = final_results
        
        # SINGLE STATUS UPDATE: Report final completion to core processor
        logger.info(f"Processing completed successfully for document {document_id}, reporting final status")
        
        # Use a more robust completion reporting mechanism
        completion_success = await report_completion_to_core_processor(document_id, job_id, final_results)
        
        if completion_success:
            logger.info(f"✅ Successfully reported completion for document {document_id}")
        else:
            logger.error(f"❌ Failed to report completion for document {document_id} - will retry")
            # Schedule retry for completion reporting
            await schedule_completion_retry(document_id, job_id, final_results)
        
        return ProcessingResponse(
            status="processing",
            job_id=job_id,
            document_id=document_id,
            message="Document processing started successfully",
            processing_steps=["text_extraction", "embedding_generation"]
        )
        
    except Exception as e:
        logger.error(f"Error processing document {request.document_id}: {e}")
        
        # Update local job status to failed
        if request.job_id in processing_jobs:
            processing_jobs[request.job_id]["status"] = "failed"
            processing_jobs[request.job_id]["error_message"] = str(e)
        
        # Report failure to core processor
        await report_failure_to_core_processor(request.document_id, request.job_id, str(e))
        
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

async def update_job_status(job_id: str, status: str, result_data: Dict[str, Any] = None, max_retries: int = 2):
    """Update job status in the core processor with retry logic"""
    for attempt in range(max_retries):
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
                return True
        except Exception as e:
            logger.warning(f"Failed to update job status for {job_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))  # Short exponential backoff
            else:
                logger.error(f"Failed to update job status for {job_id} after {max_retries} attempts: {e}")
                return False
    
    return False

async def update_document_status(document_id: str, status: str, max_retries: int = 3):
    """Update document status in the core processor with retry logic and verification"""
    for attempt in range(max_retries):
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
                
                # Verify the status was actually updated
                await asyncio.sleep(0.5)  # Small delay to ensure database update
                verification_response = await client.get(
                    f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status",
                    timeout=5.0
                )
                verification_response.raise_for_status()
                verification_data = verification_response.json()
                
                if verification_data.get("processing_status") == status:
                    logger.info(f"✅ Verified document {document_id} status is now {status}")
                    return True
                else:
                    logger.warning(f"Status verification failed for {document_id}. Expected: {status}, Got: {verification_data.get('processing_status')}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed to verify document status after {max_retries} attempts")
                        return False
                        
        except Exception as e:
            logger.warning(f"Failed to update document status for {document_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to update document status for {document_id} after {max_retries} attempts: {e}")
                return False
    
    return False

async def report_completion_to_core_processor(document_id: str, job_id: str, results: Dict[str, Any]) -> bool:
    """Report completion to core processor with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Update job status to completed
            job_success = await update_job_status(job_id, "completed", results, max_retries=1)
            if not job_success:
                logger.warning(f"Job status update failed for {job_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
            
            # Update document status to completed
            doc_success = await update_document_status(document_id, "completed", max_retries=1)
            if not doc_success:
                logger.warning(f"Document status update failed for {document_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
            
            return True
            
        except Exception as e:
            logger.warning(f"Completion reporting failed for {document_id} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                logger.error(f"Failed to report completion for {document_id} after {max_retries} attempts")
                return False
    
    return False

async def report_failure_to_core_processor(document_id: str, job_id: str, error_message: str) -> bool:
    """Report failure to core processor"""
    try:
        # Update job status to failed
        await update_job_status(job_id, "failed", {"error": error_message}, max_retries=1)
        
        # Update document status to failed
        await update_document_status(document_id, "failed", max_retries=1)
        
        logger.info(f"✅ Successfully reported failure for document {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to report failure for {document_id}: {e}")
        return False

async def schedule_completion_retry(document_id: str, job_id: str, results: Dict[str, Any]):
    """Schedule a retry for completion reporting"""
    # This could be implemented with a background task or message queue
    # For now, we'll just log it
    logger.warning(f"📅 Completion reporting for {document_id} will be retried by monitoring script")

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

@app.post("/process-sync")
async def process_document_sync(request: ProcessingRequest):
    """Process a document synchronously - complete all processing before returning"""
    try:
        logger.info(f"Starting SYNC processing for document {request.document_id}, job {request.job_id}")
        
        # Initialize job tracking
        job_id = request.job_id
        document_id = request.document_id
        
        # Step 1: Get document information
        logger.info(f"Step 1/3: Getting document information for {document_id}")
        document_info = await get_document_info(document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            raise Exception("Document file path not found")
        
        # Step 2: Extract text from document
        logger.info(f"Step 2/3: Extracting text from {file_path}")
        text_result = await extract_text_from_document(document_id, file_path)
        
        if not text_result.get("success"):
            raise Exception(f"Text extraction failed: {text_result.get('error', 'Unknown error')}")
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            raise Exception("No text content extracted from document")
        
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
        
        if embedding_result.get("status") != "completed":
            raise Exception(f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}")
        
        # Prepare final results
        final_results = {
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": 0,  # Will be calculated
            "embedding_result": embedding_result,
            "text_extracted": True,
            "text_content_length": len(text_content)
        }
        
        # GUARANTEED STATUS UPDATE: Update both job and document status before returning
        logger.info(f"Processing completed for document {document_id}, updating status synchronously")
        
        # Update job status to completed
        job_update_success = await update_job_status(job_id, "completed", final_results, max_retries=3)
        if not job_update_success:
            raise Exception(f"Failed to update job status for {job_id}")
        
        # Update document status to completed
        doc_update_success = await update_document_status(document_id, "completed", max_retries=3)
        if not doc_update_success:
            raise Exception(f"Failed to update document status for {document_id}")
        
        logger.info(f"✅ SYNC processing completed successfully for document {document_id}")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "document_id": document_id,
            "message": "Document processed successfully",
            "results": final_results
        }
        
    except Exception as e:
        logger.error(f"Error in SYNC processing for document {request.document_id}: {e}")
        
        # GUARANTEED FAILURE UPDATE: Update both job and document status to failed
        try:
            await update_job_status(request.job_id, "failed", {"error": str(e)}, max_retries=3)
            await update_document_status(request.document_id, "failed", max_retries=3)
        except Exception as update_error:
            logger.error(f"Failed to update failure status: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/process-queue")
async def process_document_queue(request: ProcessingRequest):
    """Enqueue a document for processing using Redis queue"""
    try:
        logger.info(f"Enqueuing document {request.document_id} for queue processing")
        
        # Get document information
        document_info = await get_document_info(request.document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            raise Exception("Document file path not found")
        
        # Create processing job
        job = ProcessingJob(
            document_id=request.document_id,
            job_id=request.job_id,
            file_path=file_path,
            filename=document_info.get("filename", ""),
            document_type=document_info.get("document_type", ""),
            created_at=datetime.utcnow().isoformat(),
            priority=1
        )
        
        # Enqueue the job
        success = await queue_manager.enqueue_processing_job(job)
        
        if not success:
            raise Exception("Failed to enqueue processing job")
        
        logger.info(f"✅ Successfully enqueued document {request.document_id} for processing")
        
        return {
            "status": "queued",
            "job_id": request.job_id,
            "document_id": request.document_id,
            "message": "Document queued for processing",
            "queue_position": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error enqueuing document {request.document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error enqueuing document: {str(e)}")

@app.post("/process-queue-worker")
async def process_queue_worker():
    """Worker endpoint to process jobs from the queue"""
    try:
        # Get job from queue
        job = await queue_manager.dequeue_processing_job(timeout=5)
        
        if not job:
            return {"status": "no_jobs", "message": "No jobs in queue"}
        
        logger.info(f"🔄 Processing queued job for document {job.document_id}")
        
        try:
            # Process the document
            result = await process_document_from_queue(job)
            
            # Enqueue success status update
            status_update = StatusUpdate(
                document_id=job.document_id,
                job_id=job.job_id,
                status="completed",
                results=result
            )
            
            await queue_manager.enqueue_status_update(status_update)
            logger.info(f"✅ Successfully processed queued job for document {job.document_id}")
            
            return {
                "status": "processed",
                "document_id": job.document_id,
                "job_id": job.job_id,
                "results": result
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process queued job for document {job.document_id}: {e}")
            
            # Enqueue failure status update
            status_update = StatusUpdate(
                document_id=job.document_id,
                job_id=job.job_id,
                status="failed",
                results={},
                error_message=str(e)
            )
            
            await queue_manager.enqueue_status_update(status_update)
            
            # Enqueue for retry
            await queue_manager.enqueue_failed_job(job, str(e), retry_count=0)
            
            return {
                "status": "failed",
                "document_id": job.document_id,
                "job_id": job.job_id,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"Error in queue worker: {e}")
        raise HTTPException(status_code=500, detail=f"Queue worker error: {str(e)}")

@app.get("/queue-worker/health")
async def queue_worker_health():
    """Health check endpoint for queue worker"""
    return {"status": "healthy", "service": "queue-worker"}

@app.get("/status-worker/health")
async def status_worker_health():
    """Health check endpoint for status worker"""
    return {"status": "healthy", "service": "status-worker"}

@app.post("/process-status-update")
async def process_status_update():
    """Worker endpoint to process status updates from the queue"""
    try:
        # Get status update from queue
        status_update = await queue_manager.dequeue_status_update(timeout=5)
        
        if not status_update:
            return {"status": "no_updates", "message": "No status updates in queue"}
        
        logger.info(f"🔄 Processing status update for document {status_update.document_id}")
        
        try:
            # Update job status in core processor
            job_success = await update_job_status(status_update.job_id, status_update.status, status_update.results)
            
            if not job_success:
                logger.warning(f"Failed to update job status for {status_update.job_id}")
            
            # Update document status in core processor
            doc_success = await update_document_status(status_update.document_id, status_update.status)
            
            if not doc_success:
                logger.warning(f"Failed to update document status for {status_update.document_id}")
            
            if job_success and doc_success:
                logger.info(f"✅ Successfully processed status update for document {status_update.document_id}")
                return {
                    "status": "processed",
                    "document_id": status_update.document_id,
                    "job_id": status_update.job_id,
                    "status_update": status_update.status
                }
            else:
                logger.error(f"❌ Failed to process status update for document {status_update.document_id}")
                return {
                    "status": "failed",
                    "document_id": status_update.document_id,
                    "job_id": status_update.job_id,
                    "error": "Failed to update job or document status"
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to process status update for document {status_update.document_id}: {e}")
            return {
                "status": "failed",
                "document_id": status_update.document_id,
                "job_id": status_update.job_id,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"Error in status update worker: {e}")
        raise HTTPException(status_code=500, detail=f"Status update worker error: {str(e)}")

async def process_document_from_queue(job: ProcessingJob) -> Dict[str, Any]:
    """Process a document from the queue"""
    try:
        logger.info(f"Processing queued document: {job.document_id}")
        
        # Step 1: Extract text from document
        logger.info(f"Step 1/2: Extracting text from {job.file_path}")
        text_result = await extract_text_from_document(job.document_id, job.file_path)
        
        if not text_result.get("success"):
            raise Exception(f"Text extraction failed: {text_result.get('error', 'Unknown error')}")
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            raise Exception("No text content extracted from document")
        
        # Step 2: Generate embeddings
        logger.info(f"Step 2/2: Generating embeddings for {len(text_content)} characters of text")
        embedding_result = await generate_embeddings(
            job.document_id, 
            text_content, 
            metadata={
                "filename": job.filename,
                "document_type": job.document_type,
                "file_path": job.file_path
            }
        )
        
        if embedding_result.get("status") != "completed":
            raise Exception(f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}")
        
        # Prepare results
        results = {
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": 0,  # Will be calculated
            "embedding_result": embedding_result,
            "text_extracted": True,
            "text_content_length": len(text_content)
        }
        
        logger.info(f"✅ Successfully processed queued document {job.document_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error processing queued document {job.document_id}: {e}")
        raise

@app.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics"""
    try:
        stats = await queue_manager.get_queue_stats()
        return {
            "queue_stats": stats,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting queue stats: {str(e)}")

@app.post("/queue/clear")
async def clear_queues():
    """Clear all queues (for testing/debugging)"""
    try:
        await queue_manager.clear_queues()
        return {
            "status": "success",
            "message": "All queues cleared"
        }
    except Exception as e:
        logger.error(f"Error clearing queues: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing queues: {str(e)}")

@app.get("/queue/retry-jobs")
async def get_retry_jobs():
    """Get jobs ready for retry"""
    try:
        retry_jobs = await queue_manager.get_retry_jobs()
        return {
            "retry_jobs": retry_jobs,
            "count": len(retry_jobs),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting retry jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting retry jobs: {str(e)}")

@app.post("/process-atomic")
async def process_document_atomic(request: ProcessingRequest):
    """Process a document with atomic database transactions"""
    try:
        logger.info(f"Starting ATOMIC processing for document {request.document_id}, job {request.job_id}")
        
        # Get document information
        document_info = await get_document_info(request.document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            raise Exception("Document file path not found")
        
        # Step 1: Extract text from document
        logger.info(f"Step 1/3: Extracting text from {file_path}")
        text_result = await extract_text_from_document(request.document_id, file_path)
        
        if not text_result.get("success"):
            raise Exception(f"Text extraction failed: {text_result.get('error', 'Unknown error')}")
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            raise Exception("No text content extracted from document")
        
        # Update progress atomically
        progress_results = {
            "current_step": "embedding_generation",
            "progress": 60,
            "text_extracted": True,
            "text_content_length": len(text_content)
        }
        await state_manager.update_job_progress(request.job_id, 60, "embedding_generation", progress_results)
        
        # Step 2: Generate embeddings
        logger.info(f"Step 2/3: Generating embeddings for {len(text_content)} characters of text")
        embedding_result = await generate_embeddings(
            request.document_id, 
            text_content, 
            metadata={
                "filename": document_info.get("filename"),
                "document_type": document_info.get("document_type"),
                "file_path": file_path
            }
        )
        
        if embedding_result.get("status") != "completed":
            raise Exception(f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}")
        
        # Prepare final results
        final_results = {
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": 0,  # Will be calculated
            "embedding_result": embedding_result,
            "text_extracted": True,
            "text_content_length": len(text_content),
            "current_step": "completed",
            "progress": 100
        }
        
        # ATOMIC STATUS UPDATE: Update both job and document status in single transaction
        logger.info(f"Processing completed for document {request.document_id}, performing atomic status update")
        
        success = await state_manager.atomic_status_update(
            document_id=request.document_id,
            job_id=request.job_id,
            status="completed",
            results=final_results
        )
        
        if success:
            logger.info(f"✅ ATOMIC processing completed successfully for document {request.document_id}")
        else:
            raise Exception("Failed to update status atomically")
        
        return {
            "status": "completed",
            "job_id": request.job_id,
            "document_id": request.document_id,
            "message": "Document processed successfully with atomic updates",
            "results": final_results
        }
        
    except Exception as e:
        logger.error(f"Error in ATOMIC processing for document {request.document_id}: {e}")
        
        # ATOMIC FAILURE UPDATE: Update both job and document status to failed
        try:
            await state_manager.atomic_status_update(
                document_id=request.document_id,
                job_id=request.job_id,
                status="failed",
                error_message=str(e)
            )
        except Exception as update_error:
            logger.error(f"Failed to update failure status atomically: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/state/{document_id}")
async def get_document_state(document_id: str):
    """Get current processing state for a document"""
    try:
        state = await state_manager.get_processing_state(document_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "document_id": state.document_id,
            "job_id": state.job_id,
            "status": state.status,
            "current_step": state.current_step,
            "progress": state.progress,
            "results": state.results,
            "error_message": state.error_message,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "updated_at": state.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document state for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting document state: {str(e)}")

@app.get("/state/stuck-documents")
async def get_stuck_documents(max_minutes: int = 30):
    """Get documents that might be stuck in processing"""
    try:
        stuck_documents = await state_manager.get_stuck_documents(max_minutes)
        
        return {
            "stuck_documents": stuck_documents,
            "count": len(stuck_documents),
            "max_minutes": max_minutes,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting stuck documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stuck documents: {str(e)}")

@app.post("/state/cleanup")
async def cleanup_old_jobs(days_old: int = 7):
    """Clean up old completed/failed jobs"""
    try:
        deleted_count = await state_manager.cleanup_old_jobs(days_old)
        
        return {
            "deleted_count": deleted_count,
            "days_old": days_old,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up old jobs: {str(e)}")

# Initialize queue manager on startup
@app.on_event("startup")
async def startup_event():
    """Initialize queue manager and state manager on startup"""
    try:
        # Initialize queue manager
        await queue_manager.connect()
        logger.info("✅ Queue manager initialized")
        
        # Initialize state manager (we'll need to get the database URL from environment)
        # For now, we'll skip this and use the existing status update methods
        logger.info("✅ State manager ready (using existing methods)")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize managers: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup managers on shutdown"""
    try:
        await queue_manager.disconnect()
        await state_manager.disconnect()
        logger.info("Managers disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting managers: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 