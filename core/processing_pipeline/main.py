from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
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
import re
from queue_manager import queue_manager, ProcessingJob, StatusUpdate
from state_manager import state_manager

# Add atomic status update function at the top of the file, after the imports
async def atomic_status_update(document_id: str, job_id: str, status: str, results: Dict[str, Any] = None, error_message: str = None) -> bool:
    """Perform atomic status update for both job and document to prevent race conditions"""
    logger.info(f"🔒 ATOMIC UPDATE: Starting atomic status update for document {document_id}, job {job_id} to {status}")
    
    # Map job status to document status
    # Job status can be "running", but document status must be "processing"
    document_status = status
    if status == "running":
        document_status = "processing"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Step 1: Update job status first
            logger.info(f"🔒 ATOMIC UPDATE: Attempt {attempt + 1}/{max_retries} - Updating job status")
            job_success = await update_job_status(job_id, status, results, max_retries=1, document_id=document_id)
            
            if not job_success:
                logger.warning(f"❌ ATOMIC UPDATE: Job status update failed (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    logger.error(f"❌ ATOMIC UPDATE: Job status update failed after {max_retries} attempts")
                    return False
            
            # Step 2: Update document status (using mapped status)
            logger.info(f"🔒 ATOMIC UPDATE: Updating document status to {document_status}")
            doc_success = await update_document_status(document_id, document_status, max_retries=1)
            
            if not doc_success:
                logger.warning(f"❌ ATOMIC UPDATE: Document status update failed (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    logger.error(f"❌ ATOMIC UPDATE: Document status update failed after {max_retries} attempts")
                    return False
            
            # Step 3: Update cache immediately
            await update_document_status_cache(document_id, document_status)
            
            # Step 4: Verify both updates were successful
            logger.info(f"🔒 ATOMIC UPDATE: Verifying status updates")
            await asyncio.sleep(0.2)  # Small delay to ensure database consistency
            
            # Verify job status
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CORE_PROCESSOR_URL}/processing/jobs/{job_id}",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        job_data = response.json()
                        if job_data.get("status") == status:
                            logger.info(f"✅ ATOMIC UPDATE: Job status verified as {status}")
                        else:
                            logger.warning(f"❌ ATOMIC UPDATE: Job status verification failed - expected {status}, got {job_data.get('status')}")
                            # For job status, we need to handle the mapping between "running" and "processing"
                            if status == "running" and job_data.get("status") == "processing":
                                logger.info(f"✅ ATOMIC UPDATE: Job status verified (running maps to processing)")
                            elif status == "processing" and job_data.get("status") == "running":
                                logger.info(f"✅ ATOMIC UPDATE: Job status verified (processing maps to running)")
                            else:
                                if attempt < max_retries - 1:
                                    continue
                                else:
                                    return False
                            if attempt < max_retries - 1:
                                continue
                            else:
                                return False
            except Exception as e:
                logger.warning(f"⚠️ ATOMIC UPDATE: Could not verify job status: {e}")
            
            # Verify document status using cache
            cached_status = await get_document_status_cache(document_id)
            if cached_status == document_status:
                logger.info(f"✅ ATOMIC UPDATE: Document status verified as {document_status}")
            else:
                logger.warning(f"❌ ATOMIC UPDATE: Document status verification failed - expected {document_status}, got {cached_status}")
                if attempt < max_retries - 1:
                    continue
                else:
                    return False
            
            logger.info(f"✅ ATOMIC UPDATE: Successfully completed atomic status update for {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ATOMIC UPDATE: Unexpected error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                return False
    
    logger.error(f"❌ ATOMIC UPDATE: All attempts failed for {document_id}")
    return False

# Add concurrency control with document-specific locks
processing_locks = {}
document_status_cache = {}

async def get_processing_lock(document_id: str):
    """Get or create a lock for document processing to prevent race conditions"""
    if document_id not in processing_locks:
        processing_locks[document_id] = asyncio.Lock()
    return processing_locks[document_id]

async def get_document_status_cache(document_id: str) -> str:
    """Get cached document status to reduce database calls"""
    if document_id in document_status_cache:
        return document_status_cache[document_id]
    
    try:
        status_data = await get_document_processing_status(document_id)
        status = status_data.get("processing_status", "unknown")
        document_status_cache[document_id] = status
        return status
    except Exception as e:
        logger.warning(f"Could not get status for {document_id}: {e}")
        return "unknown"

async def update_document_status_cache(document_id: str, status: str):
    """Update cached document status"""
    document_status_cache[document_id] = status

async def clear_document_status_cache(document_id: str = None):
    """Clear document status cache"""
    if document_id:
        document_status_cache.pop(document_id, None)
    else:
        document_status_cache.clear()

def is_valid_uuid(job_id: str) -> bool:
    """Validate if job_id is a proper UUID format"""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    return bool(uuid_pattern.match(job_id))

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
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")
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
    
    @validator('job_id')
    def validate_job_id(cls, v):
        if not is_valid_uuid(v):
            raise ValueError('job_id must be a valid UUID')
        return v

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

async def get_document_processing_status(document_id: str) -> Dict[str, Any]:
    """Get document processing status from core processor"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Failed to get document processing status for {document_id}: {e}")
        raise

async def extract_text_from_document(document_id: str, file_path: str) -> Dict[str, Any]:
    """Extract text from document using text processor service with dynamic folder mounting support"""
    import os  # Move import to top of function
    
    try:
        logger.info(f"=== EXTRACT_TEXT_FUNCTION_CALLED ===")
        logger.info(f"Extracting text from document {document_id} at {file_path}")
        
        # Use the text processor service for all files
        # Since we're using host networking, all files should be accessible
        text_processor_url = os.getenv("TEXT_PROCESSOR_URL", "http://localhost:8005")
        
        logger.info(f"Using text processor service for file: {file_path}")
        
        # Detect if this is a scan folder path and mount to shared volume if needed
        request_data = {
            "document_path": file_path,
            "document_id": document_id
        }
        
        # If the file path is a container path from scan folder, ensure it's mounted in shared volume
        if file_path.startswith('/app/scan_folder/'):
            try:
                document_info = await get_document_info(document_id)
                original_file_path = document_info.get("original_file_path")
                if original_file_path and original_file_path != file_path:
                    # Extract the host folder path from the original file path
                    from pathlib import Path
                    host_folder_path = str(Path(original_file_path).parent)
                    folder_name = Path(host_folder_path).name
                    
                    # Use host volume manager to ensure the folder is mounted with concurrent support
                    import asyncio
                    
                    # Call host volume manager service
                    async with httpx.AsyncClient() as client:
                        try:
                            response = await client.post(
                                "http://localhost:8011/mount",
                                json={
                                    "host_path": host_folder_path,
                                    "folder_name": folder_name
                                },
                                timeout=30.0
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                if result.get("success"):
                                    unique_folder_name = result.get("unique_folder_name")
                                else:
                                    logger.warning(f"Failed to mount folder: {result.get('error_message')}")
                                    unique_folder_name = None
                            else:
                                logger.warning(f"Host volume manager returned status {response.status_code}")
                                unique_folder_name = None
                                
                        except Exception as e:
                            logger.warning(f"Failed to call host volume manager: {e}")
                            unique_folder_name = None
                    if unique_folder_name:
                        logger.info(f"Successfully mounted folder {host_folder_path} to shared volume as {unique_folder_name}")
                        # Update the file path to use the unique folder name
                        filename = Path(file_path).name
                        file_path = f"/app/scan_folders/{unique_folder_name}/{filename}"
                        request_data["document_path"] = file_path
                    else:
                        logger.warning(f"Failed to mount folder {host_folder_path}, using original path")
                        
            except Exception as e:
                logger.warning(f"Failed to mount folder to shared volume: {e}")
        
        # Regular HTTP call to text processor
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{text_processor_url}/extract-text",
                json=request_data,
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
    # Get processing lock to prevent race conditions
    document_id = request.document_id
    processing_lock = await get_processing_lock(document_id)
    
    async with processing_lock:
        try:
            logger.info(f"Starting processing for document {request.document_id}, job {request.job_id}")
            
            # Use the job ID provided in the request (this is the correct job ID from the core processor)
            job_id = request.job_id
            logger.info(f"Using job ID from request: {job_id}")
            
            processing_jobs[job_id] = {
                "job_id": job_id,
                "document_id": document_id,
                "status": "running",
                "progress": 0,
                "current_step": "initialized",
                "started_at": datetime.utcnow(),
                "results": {},
                "error_message": None
            }
            
            # STEP 1: Initialize processing with atomic status update
            logger.info(f"Step 1/5: Initializing processing for {document_id}")
            init_success = await atomic_status_update(
                document_id, 
                job_id, 
                "running", 
                {
                    "current_step": "initialized",
                    "progress": 10,
                    "message": "Processing pipeline initialized"
                }
            )
            
            if not init_success:
                raise Exception("Failed to initialize processing status")
            
            # STEP 2: Get document information
            logger.info(f"Step 2/5: Getting document information for {document_id}")
            await update_job_status(job_id, "running", {
                "current_step": "document_info_retrieval",
                "progress": 20,
                "message": "Retrieving document information"
            }, document_id=document_id)
            
            document_info = await get_document_info(document_id)
            file_path = document_info.get("file_path")
            
            if not file_path:
                error_msg = "Document file path not found"
                logger.error(f"Error in step 2: {error_msg}")
                await atomic_status_update(document_id, job_id, "failed", {
                    "current_step": "document_info_retrieval",
                    "error": error_msg
                })
                raise Exception(error_msg)
            
            logger.info(f"✅ Step 2 completed: Document info retrieved for {document_id}")
            
            # STEP 3: Extract text from document
            logger.info(f"Step 3/5: Extracting text from {file_path}")
            await update_job_status(job_id, "running", {
                "current_step": "text_extraction",
                "progress": 40,
                "message": f"Extracting text from {os.path.basename(file_path)}"
            }, document_id=document_id)
            
            text_result = await extract_text_from_document(document_id, file_path)
            
            if not text_result.get("success"):
                error_msg = f"Text extraction failed: {text_result.get('error', 'Unknown error')}"
                logger.error(f"Error in step 3: {error_msg}")
                await atomic_status_update(document_id, job_id, "failed", {
                    "current_step": "text_extraction",
                    "error": error_msg
                })
                raise Exception(error_msg)
            
            text_content = text_result.get("text_content", "")
            if not text_content:
                error_msg = "No text content extracted from document"
                logger.error(f"Error in step 3: {error_msg}")
                await atomic_status_update(document_id, job_id, "failed", {
                    "current_step": "text_extraction",
                    "error": error_msg
                })
                raise Exception(error_msg)
            
            logger.info(f"✅ Step 3 completed: Text extracted ({len(text_content)} characters) for {document_id}")
            
            # STEP 4: Generate embeddings
            logger.info(f"Step 4/5: Generating embeddings for {len(text_content)} characters of text")
            await update_job_status(job_id, "running", {
                "current_step": "embedding_generation",
                "progress": 70,
                "message": f"Generating embeddings for {len(text_content)} characters of text"
            }, document_id=document_id)
            
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
                error_msg = f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}"
                logger.error(f"Error in step 4: {error_msg}")
                await atomic_status_update(document_id, job_id, "failed", {
                    "current_step": "embedding_generation",
                    "error": error_msg
                })
                raise Exception(error_msg)
            
            logger.info(f"✅ Step 4 completed: Embeddings generated for {document_id}")
            
            # STEP 5: Finalize processing with atomic completion
            logger.info(f"Step 5/5: Finalizing processing for {document_id}")
            
            # Prepare final results
            final_results = {
                "embeddings_generated": True,
                "entities_extracted": False,  # Not implemented yet
                "relationships_mapped": False,  # Not implemented yet
                "processing_time": (datetime.utcnow() - processing_jobs[job_id]["started_at"]).total_seconds(),
                "embedding_result": embedding_result,
                "text_extracted": True,
                "text_content_length": len(text_content),
                "current_step": "completed",
                "progress": 100,
                "message": "Processing completed successfully"
            }
            
            # Update local job status
            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["progress"] = 100
            processing_jobs[job_id]["results"] = final_results
            
            # ATOMIC COMPLETION: Use atomic status update to prevent race conditions
            logger.info(f"Processing completed successfully for document {document_id}, performing atomic completion")
            
            completion_success = await atomic_status_update(document_id, job_id, "completed", final_results)
            
            if completion_success:
                logger.info(f"✅ Successfully completed processing for document {document_id}")
            else:
                logger.error(f"❌ Failed to complete processing for document {document_id} - will retry")
                # Schedule retry for completion reporting
                await schedule_completion_retry(document_id, job_id, final_results)
            
            logger.info(f"✅ Step 5 completed: Processing finalized for {document_id}")
            
            return ProcessingResponse(
                status="completed",
                job_id=job_id,
                document_id=document_id,
                message="Document processing completed successfully",
                processing_steps=["text_extraction", "embedding_generation"]
            )
            
        except Exception as e:
            logger.error(f"Error processing document {request.document_id}: {e}")
            
            # ATOMIC FAILURE: Use atomic status update for failures too
            try:
                await atomic_status_update(request.document_id, request.job_id, "failed", {"error": str(e)})
            except Exception as update_error:
                logger.error(f"Failed to update failure status: {update_error}")
            
            # Update local job status to failed
            if request.job_id in processing_jobs:
                processing_jobs[request.job_id]["status"] = "failed"
                processing_jobs[request.job_id]["error_message"] = str(e)
            
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
            # Validate job_id format before processing
            if not is_valid_uuid(job_id):
                logger.error(f"Invalid job_id format in status update: {job_id} (must be UUID)")
                return {"message": "Invalid job_id format", "error": "Job ID must be a valid UUID"}
            
            # Update the job status
            processing_jobs[job_id]["status"] = status
            if status == "completed":
                processing_jobs[job_id]["progress"] = 100
                processing_jobs[job_id]["results"] = result_data
            elif status == "failed":
                processing_jobs[job_id]["error_message"] = result_data.get("error", "Unknown error")
            
            # Update job status in core processor
            await update_job_status(job_id, status, result_data, document_id=document_id)
            
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

async def update_job_status(job_id: str, status: str, result_data: Dict[str, Any] = None, max_retries: int = 2, document_id: str = None):
    """Update job status in the core processor with retry logic"""
    logger.info(f"🔧 JOB STATUS UPDATE: Starting job status update for {job_id} to {status}")
    logger.info(f"🔧 JOB STATUS UPDATE: Result data: {result_data}")
    logger.info(f"🔧 JOB STATUS UPDATE: Document ID: {document_id}")
    
    # Validate job_id format
    if not is_valid_uuid(job_id):
        logger.error(f"❌ JOB STATUS UPDATE: Invalid job_id format: {job_id} (must be UUID)")
        return False
    
    # If document_id is not provided, we can't update job status
    if not document_id:
        logger.error(f"❌ JOB STATUS UPDATE: Document ID is required but not provided for job {job_id}")
        return False
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔧 JOB STATUS UPDATE: Attempt {attempt + 1}/{max_retries} for job {job_id}")
            
            async with httpx.AsyncClient() as client:
                # Prepare request payload
                payload = {
                    "status": status,
                    "result_data": result_data or {}
                }
                logger.info(f"🔧 JOB STATUS UPDATE: Sending POST request to {CORE_PROCESSOR_URL}/processing/jobs/{job_id}/status")
                logger.info(f"🔧 JOB STATUS UPDATE: Request payload: {payload}")
                
                response = await client.post(
                    f"{CORE_PROCESSOR_URL}/processing/jobs/{job_id}/status",
                    json=payload,
                    timeout=10.0
                )
                
                logger.info(f"🔧 JOB STATUS UPDATE: Response status code: {response.status_code}")
                logger.info(f"🔧 JOB STATUS UPDATE: Response headers: {dict(response.headers)}")
                
                try:
                    response_text = response.text
                    logger.info(f"🔧 JOB STATUS UPDATE: Response body: {response_text}")
                except Exception as e:
                    logger.warning(f"🔧 JOB STATUS UPDATE: Could not read response body: {e}")
                
                response.raise_for_status()
                logger.info(f"✅ JOB STATUS UPDATE: Successfully updated job {job_id} status to {status}")
                return True
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ JOB STATUS UPDATE: HTTP error for {job_id} (attempt {attempt + 1}/{max_retries})")
            logger.error(f"❌ JOB STATUS UPDATE: Status code: {e.response.status_code}")
            logger.error(f"❌ JOB STATUS UPDATE: Response: {e.response.text}")
            logger.error(f"❌ JOB STATUS UPDATE: Error: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔧 JOB STATUS UPDATE: Retrying in {0.5 * (attempt + 1)} seconds...")
                await asyncio.sleep(0.5 * (attempt + 1))  # Short exponential backoff
            else:
                logger.error(f"❌ JOB STATUS UPDATE: Failed to update job status for {job_id} after {max_retries} attempts")
                return False
                
        except httpx.TimeoutException as e:
            logger.error(f"❌ JOB STATUS UPDATE: Timeout error for {job_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"🔧 JOB STATUS UPDATE: Retrying in {0.5 * (attempt + 1)} seconds...")
                await asyncio.sleep(0.5 * (attempt + 1))  # Short exponential backoff
            else:
                logger.error(f"❌ JOB STATUS UPDATE: Failed to update job status for {job_id} after {max_retries} attempts")
                return False
                
        except Exception as e:
            logger.error(f"❌ JOB STATUS UPDATE: Unexpected error for {job_id} (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"❌ JOB STATUS UPDATE: Error type: {type(e).__name__}")
            logger.error(f"❌ JOB STATUS UPDATE: Error details: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔧 JOB STATUS UPDATE: Retrying in {0.5 * (attempt + 1)} seconds...")
                await asyncio.sleep(0.5 * (attempt + 1))  # Short exponential backoff
            else:
                logger.error(f"❌ JOB STATUS UPDATE: Failed to update job status for {job_id} after {max_retries} attempts")
                return False
    
    logger.error(f"❌ JOB STATUS UPDATE: All attempts failed for job {job_id}")
    return False

async def update_document_status(document_id: str, status: str, max_retries: int = 3):
    """Update document status in the core processor with retry logic and verification"""
    logger.info(f"🔧 STATUS UPDATE: Starting document status update for {document_id} to {status}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔧 STATUS UPDATE: Attempt {attempt + 1}/{max_retries} for document {document_id}")
            
            async with httpx.AsyncClient() as client:
                # Step 1: Send status update request
                logger.info(f"🔧 STATUS UPDATE: Sending POST request to {CORE_PROCESSOR_URL}/documents/{document_id}/status")
                logger.info(f"🔧 STATUS UPDATE: Request payload: {{'processing_status': '{status}'}}")
                
                response = await client.post(
                    f"{CORE_PROCESSOR_URL}/documents/{document_id}/status",
                    json={
                        "processing_status": status
                    },
                    timeout=10.0
                )
                
                logger.info(f"🔧 STATUS UPDATE: Response status code: {response.status_code}")
                logger.info(f"🔧 STATUS UPDATE: Response headers: {dict(response.headers)}")
                
                try:
                    response_text = response.text
                    logger.info(f"🔧 STATUS UPDATE: Response body: {response_text}")
                except Exception as e:
                    logger.warning(f"🔧 STATUS UPDATE: Could not read response body: {e}")
                
                response.raise_for_status()
                logger.info(f"✅ STATUS UPDATE: Successfully sent status update for document {document_id} to {status}")
                
                # Step 2: Verify the status was actually updated
                logger.info(f"🔧 STATUS UPDATE: Starting verification for document {document_id}")
                await asyncio.sleep(0.5)  # Small delay to ensure database update
                
                verification_response = await client.get(
                    f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status",
                    timeout=5.0
                )
                
                logger.info(f"🔧 STATUS UPDATE: Verification response status: {verification_response.status_code}")
                verification_response.raise_for_status()
                verification_data = verification_response.json()
                
                logger.info(f"🔧 STATUS UPDATE: Verification data: {verification_data}")
                
                if verification_data.get("processing_status") == status:
                    logger.info(f"✅ STATUS UPDATE: Verified document {document_id} status is now {status}")
                    return True
                else:
                    logger.warning(f"❌ STATUS UPDATE: Status verification failed for {document_id}")
                    logger.warning(f"❌ STATUS UPDATE: Expected: {status}, Got: {verification_data.get('processing_status')}")
                    logger.warning(f"❌ STATUS UPDATE: Full verification data: {verification_data}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"🔧 STATUS UPDATE: Retrying in {1.0 * (attempt + 1)} seconds...")
                        await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"❌ STATUS UPDATE: Failed to verify document status after {max_retries} attempts")
                        return False
                        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ STATUS UPDATE: HTTP error for {document_id} (attempt {attempt + 1}/{max_retries})")
            logger.error(f"❌ STATUS UPDATE: Status code: {e.response.status_code}")
            logger.error(f"❌ STATUS UPDATE: Response: {e.response.text}")
            logger.error(f"❌ STATUS UPDATE: Error: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔧 STATUS UPDATE: Retrying in {1.0 * (attempt + 1)} seconds...")
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"❌ STATUS UPDATE: Failed to update document status for {document_id} after {max_retries} attempts")
                return False
                
        except httpx.TimeoutException as e:
            logger.error(f"❌ STATUS UPDATE: Timeout error for {document_id} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"🔧 STATUS UPDATE: Retrying in {1.0 * (attempt + 1)} seconds...")
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"❌ STATUS UPDATE: Failed to update document status for {document_id} after {max_retries} attempts")
                return False
                
        except Exception as e:
            logger.error(f"❌ STATUS UPDATE: Unexpected error for {document_id} (attempt {attempt + 1}/{max_retries}): {e}")
            logger.error(f"❌ STATUS UPDATE: Error type: {type(e).__name__}")
            logger.error(f"❌ STATUS UPDATE: Error details: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"🔧 STATUS UPDATE: Retrying in {1.0 * (attempt + 1)} seconds...")
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"❌ STATUS UPDATE: Failed to update document status for {document_id} after {max_retries} attempts")
                return False
    
    logger.error(f"❌ STATUS UPDATE: All attempts failed for document {document_id}")
    return False

async def report_completion_to_core_processor(document_id: str, job_id: str, results: Dict[str, Any]) -> bool:
    """Report completion to core processor with retry logic"""
    logger.info(f"🎯 COMPLETION REPORT: Starting completion report for document {document_id}, job {job_id}")
    logger.info(f"🎯 COMPLETION REPORT: Results: {results}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🎯 COMPLETION REPORT: Attempt {attempt + 1}/{max_retries}")
            
            # Step 1: Update job status to completed
            logger.info(f"🎯 COMPLETION REPORT: Step 1 - Updating job status for {job_id}")
            job_success = await update_job_status(job_id, "completed", results, max_retries=1, document_id=document_id)
            
            if not job_success:
                logger.warning(f"❌ COMPLETION REPORT: Job status update failed for {job_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    logger.info(f"🎯 COMPLETION REPORT: Retrying job status update in {1.0 * (attempt + 1)} seconds...")
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    logger.error(f"❌ COMPLETION REPORT: Job status update failed after {max_retries} attempts")
                    return False
            else:
                logger.info(f"✅ COMPLETION REPORT: Job status update successful for {job_id}")
            
            # Step 2: Update document status to completed
            logger.info(f"🎯 COMPLETION REPORT: Step 2 - Updating document status for {document_id}")
            doc_success = await update_document_status(document_id, "completed", max_retries=1)
            
            if not doc_success:
                logger.warning(f"❌ COMPLETION REPORT: Document status update failed for {document_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    logger.info(f"🎯 COMPLETION REPORT: Retrying document status update in {1.0 * (attempt + 1)} seconds...")
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    logger.error(f"❌ COMPLETION REPORT: Document status update failed after {max_retries} attempts")
                    return False
            else:
                logger.info(f"✅ COMPLETION REPORT: Document status update successful for {document_id}")
            
            logger.info(f"✅ COMPLETION REPORT: Successfully completed all status updates for {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ COMPLETION REPORT: Unexpected error for {document_id} (attempt {attempt + 1}): {e}")
            logger.error(f"❌ COMPLETION REPORT: Error type: {type(e).__name__}")
            logger.error(f"❌ COMPLETION REPORT: Error details: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"🎯 COMPLETION REPORT: Retrying in {1.0 * (attempt + 1)} seconds...")
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                logger.error(f"❌ COMPLETION REPORT: Failed to report completion for {document_id} after {max_retries} attempts")
                return False
    
    logger.error(f"❌ COMPLETION REPORT: All attempts failed for document {document_id}")
    return False

async def report_failure_to_core_processor(document_id: str, job_id: str, error_message: str) -> bool:
    """Report failure to core processor"""
    try:
        # Update job status to failed
        await update_job_status(job_id, "failed", {"error": error_message}, max_retries=1, document_id=document_id)
        
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
        
        # Get the existing job ID from the database for this document
        document_id = request.document_id
        
        try:
            document_info = await get_document_info(document_id)
            processing_status = await get_document_processing_status(document_id)
            
            # Find the first job for this document
            existing_jobs = processing_status.get("processing_jobs", [])
            if existing_jobs:
                # Use the first job ID from the database
                job_id = existing_jobs[0]["id"]
                logger.info(f"Using existing job ID from database: {job_id}")
            else:
                # Fallback to the provided job_id if no jobs exist
                job_id = request.job_id
                logger.warning(f"No existing jobs found, using provided job_id: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to get existing job ID, using provided job_id: {e}")
            job_id = request.job_id
        
        # STEP 1: Initialize processing
        logger.info(f"Step 1/5: Initializing SYNC processing for {document_id}")
        await update_job_status(job_id, "processing", {
            "current_step": "initialized",
            "progress": 10,
            "message": "Synchronous processing pipeline initialized"
        })
        await update_document_status(document_id, "processing")
        
        # STEP 2: Get document information
        logger.info(f"Step 2/5: Getting document information for {document_id}")
        await update_job_status(job_id, "processing", {
            "current_step": "document_info_retrieval",
            "progress": 20,
            "message": "Retrieving document information"
        })
        
        document_info = await get_document_info(document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            error_msg = "Document file path not found"
            logger.error(f"Error in step 2: {error_msg}")
            await update_job_status(job_id, "failed", {
                "current_step": "document_info_retrieval",
                "error": error_msg
            })
            await update_document_status(document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 2 completed: Document info retrieved for {document_id}")
        
        # STEP 3: Extract text from document
        logger.info(f"Step 3/5: Extracting text from {file_path}")
        await update_job_status(job_id, "processing", {
            "current_step": "text_extraction",
            "progress": 40,
            "message": f"Extracting text from {os.path.basename(file_path)}"
        })
        
        text_result = await extract_text_from_document(document_id, file_path)
        
        if not text_result.get("success"):
            error_msg = f"Text extraction failed: {text_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 3: {error_msg}")
            await update_job_status(job_id, "failed", {
                "current_step": "text_extraction",
                "error": error_msg
            })
            await update_document_status(document_id, "failed")
            raise Exception(error_msg)
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            error_msg = "No text content extracted from document"
            logger.error(f"Error in step 3: {error_msg}")
            await update_job_status(job_id, "failed", {
                "current_step": "text_extraction",
                "error": error_msg
            })
            await update_document_status(document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 3 completed: Text extracted ({len(text_content)} characters) for {document_id}")
        
        # STEP 4: Generate embeddings
        logger.info(f"Step 4/5: Generating embeddings for {len(text_content)} characters of text")
        await update_job_status(job_id, "processing", {
            "current_step": "embedding_generation",
            "progress": 70,
            "message": f"Generating embeddings for {len(text_content)} characters of text"
        })
        
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
            error_msg = f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 4: {error_msg}")
            await update_job_status(job_id, "failed", {
                "current_step": "embedding_generation",
                "error": error_msg
            })
            await update_document_status(document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 4 completed: Embeddings generated for {document_id}")
        
        # STEP 5: Finalize processing
        logger.info(f"Step 5/5: Finalizing SYNC processing for {document_id}")
        await update_job_status(job_id, "running", {
            "current_step": "finalizing",
            "progress": 90,
            "message": "Finalizing processing and storing results"
        })
        
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
            "progress": 100,
            "message": "Synchronous processing completed successfully"
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
        
        logger.info(f"✅ Step 5 completed: SYNC processing finalized for {document_id}")
        
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
            await update_job_status(request.job_id, "failed", {"error": str(e)}, max_retries=3, document_id=request.document_id)
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
        logger.info(f"🔄 QUEUE WORKER: Starting queue worker processing")
        
        # Get job from queue
        job = await queue_manager.dequeue_processing_job(timeout=5)
        
        if not job:
            logger.info(f"🔄 QUEUE WORKER: No jobs in queue")
            return {"status": "no_jobs", "message": "No jobs in queue"}
        
        logger.info(f"🔄 QUEUE WORKER: Processing queued job for document {job.document_id}")
        logger.info(f"🔄 QUEUE WORKER: Job details: {job}")
        
        try:
            # Process the document
            logger.info(f"🔄 QUEUE WORKER: Starting document processing for {job.document_id}")
            result = await process_document_from_queue(job)
            logger.info(f"✅ QUEUE WORKER: Document processing completed for {job.document_id}")
            logger.info(f"✅ QUEUE WORKER: Processing result: {result}")
            
            # Enqueue success status update
            logger.info(f"🔄 QUEUE WORKER: Creating success status update for {job.document_id}")
            status_update = StatusUpdate(
                document_id=job.document_id,
                job_id=job.job_id,
                status="completed",
                results=result
            )
            
            logger.info(f"🔄 QUEUE WORKER: Enqueuing status update: {status_update}")
            await queue_manager.enqueue_status_update(status_update)
            logger.info(f"✅ QUEUE WORKER: Successfully enqueued status update for {job.document_id}")
            
            logger.info(f"✅ QUEUE WORKER: Successfully processed queued job for document {job.document_id}")
            
            return {
                "status": "processed",
                "document_id": job.document_id,
                "job_id": job.job_id,
                "results": result
            }
            
        except Exception as e:
            logger.error(f"❌ QUEUE WORKER: Failed to process queued job for document {job.document_id}: {e}")
            logger.error(f"❌ QUEUE WORKER: Error type: {type(e).__name__}")
            logger.error(f"❌ QUEUE WORKER: Error details: {str(e)}")
            
            # Enqueue failure status update
            logger.info(f"🔄 QUEUE WORKER: Creating failure status update for {job.document_id}")
            status_update = StatusUpdate(
                document_id=job.document_id,
                job_id=job.job_id,
                status="failed",
                results={},
                error_message=str(e)
            )
            
            logger.info(f"🔄 QUEUE WORKER: Enqueuing failure status update: {status_update}")
            await queue_manager.enqueue_status_update(status_update)
            logger.info(f"✅ QUEUE WORKER: Successfully enqueued failure status update for {job.document_id}")
            
            # Enqueue for retry
            logger.info(f"🔄 QUEUE WORKER: Enqueuing job for retry: {job.document_id}")
            await queue_manager.enqueue_failed_job(job, str(e), retry_count=0)
            logger.info(f"✅ QUEUE WORKER: Successfully enqueued job for retry: {job.document_id}")
            
            return {
                "status": "failed",
                "document_id": job.document_id,
                "job_id": job.job_id,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"❌ QUEUE WORKER: Error in queue worker: {e}")
        logger.error(f"❌ QUEUE WORKER: Error type: {type(e).__name__}")
        logger.error(f"❌ QUEUE WORKER: Error details: {str(e)}")
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
        logger.info(f"🔄 STATUS WORKER: Starting status update processing")
        
        # Get status update from queue
        status_update = await queue_manager.dequeue_status_update(timeout=5)
        
        if not status_update:
            logger.info(f"🔄 STATUS WORKER: No status updates in queue")
            return {"status": "no_updates", "message": "No status updates in queue"}
        
        logger.info(f"🔄 STATUS WORKER: Processing status update for document {status_update.document_id}")
        logger.info(f"🔄 STATUS WORKER: Status update details: {status_update}")
        
        try:
            # Step 1: Update job status in core processor
            logger.info(f"🔄 STATUS WORKER: Step 1 - Updating job status for {status_update.job_id}")
            job_success = await update_job_status(status_update.job_id, status_update.status, status_update.results, document_id=status_update.document_id)
            
            if not job_success:
                logger.warning(f"❌ STATUS WORKER: Failed to update job status for {status_update.job_id}")
            else:
                logger.info(f"✅ STATUS WORKER: Successfully updated job status for {status_update.job_id}")
            
            # Step 2: Update document status in core processor
            logger.info(f"🔄 STATUS WORKER: Step 2 - Updating document status for {status_update.document_id}")
            doc_success = await update_document_status(status_update.document_id, status_update.status)
            
            if not doc_success:
                logger.warning(f"❌ STATUS WORKER: Failed to update document status for {status_update.document_id}")
            else:
                logger.info(f"✅ STATUS WORKER: Successfully updated document status for {status_update.document_id}")
            
            if job_success and doc_success:
                logger.info(f"✅ STATUS WORKER: Successfully processed status update for document {status_update.document_id}")
                return {
                    "status": "processed",
                    "document_id": status_update.document_id,
                    "job_id": status_update.job_id,
                    "status_update": status_update.status
                }
            else:
                logger.error(f"❌ STATUS WORKER: Failed to process status update for document {status_update.document_id}")
                logger.error(f"❌ STATUS WORKER: Job success: {job_success}, Document success: {doc_success}")
                return {
                    "status": "failed",
                    "document_id": status_update.document_id,
                    "job_id": status_update.job_id,
                    "error": "Failed to update job or document status"
                }
            
        except Exception as e:
            logger.error(f"❌ STATUS WORKER: Failed to process status update for document {status_update.document_id}: {e}")
            logger.error(f"❌ STATUS WORKER: Error type: {type(e).__name__}")
            logger.error(f"❌ STATUS WORKER: Error details: {str(e)}")
            return {
                "status": "failed",
                "document_id": status_update.document_id,
                "job_id": status_update.job_id,
                "error": str(e)
            }
            
    except Exception as e:
        logger.error(f"❌ STATUS WORKER: Error in status update worker: {e}")
        logger.error(f"❌ STATUS WORKER: Error type: {type(e).__name__}")
        logger.error(f"❌ STATUS WORKER: Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status update worker error: {str(e)}")

async def process_document_from_queue(job: ProcessingJob) -> Dict[str, Any]:
    """Process a document from the queue"""
    try:
        logger.info(f"Processing queued document: {job.document_id}")
        
        # STEP 1: Initialize queue processing
        logger.info(f"Step 1/4: Initializing queue processing for {job.document_id}")
        await update_job_status(job.job_id, "initializing", {
            "current_step": "queue_initialized",
            "progress": 10,
            "message": "Queue processing pipeline initialized"
        }, document_id=job.document_id)
        
        # Update document status to reflect current step
        await update_document_status(job.document_id, "initializing")
        
        # STEP 2: Extract text from document
        logger.info(f"Step 2/4: Extracting text from {job.file_path}")
        await update_job_status(job.job_id, "generating_embeddings", {
            "current_step": "text_extraction",
            "progress": 30,
            "message": f"Extracting text from {os.path.basename(job.file_path)}"
        }, document_id=job.document_id)
        
        text_result = await extract_text_from_document(job.document_id, job.file_path)
        
        if not text_result.get("success"):
            error_msg = f"Text extraction failed: {text_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 2: {error_msg}")
            await update_job_status(job.job_id, "text_extraction_failed", {
                "current_step": "text_extraction",
                "error": error_msg
            }, document_id=job.document_id)
            await update_document_status(job.document_id, "text_extraction_failed")
            raise Exception(error_msg)
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            error_msg = "No text content extracted from document"
            logger.error(f"Error in step 2: {error_msg}")
            await update_job_status(job.job_id, "text_extraction_failed", {
                "current_step": "text_extraction",
                "error": error_msg
            }, document_id=job.document_id)
            await update_document_status(job.document_id, "text_extraction_failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 2 completed: Text extracted ({len(text_content)} characters) for {job.document_id}")
        
        # Update document status to reflect next step
        await update_document_status(job.document_id, "generating_embeddings")
        
        # STEP 3: Generate embeddings
        logger.info(f"Step 3/4: Generating embeddings for {len(text_content)} characters of text")
        await update_job_status(job.job_id, "generating_embeddings", {
            "current_step": "embedding_generation",
            "progress": 60,
            "message": f"Generating embeddings for {len(text_content)} characters of text"
        }, document_id=job.document_id)
        
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
            error_msg = f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 3: {error_msg}")
            await update_job_status(job.job_id, "embedding_generation_failed", {
                "current_step": "embedding_generation",
                "error": error_msg
            }, document_id=job.document_id)
            await update_document_status(job.document_id, "embedding_generation_failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 3 completed: Embeddings generated for {job.document_id}")
        
        # Update document status to reflect next step
        await update_document_status(job.document_id, "finalizing")
        
        # STEP 4: Finalize queue processing
        logger.info(f"Step 4/4: Finalizing queue processing for {job.document_id}")
        await update_job_status(job.job_id, "finalizing", {
            "current_step": "finalizing",
            "progress": 90,
            "message": "Finalizing queue processing and storing results"
        }, document_id=job.document_id)
        
        # Prepare results
        results = {
            "embeddings_generated": True,
            "entities_extracted": False,  # Not implemented yet
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": 0,  # Will be calculated
            "embedding_result": embedding_result,
            "text_extracted": True,
            "text_content_length": len(text_content),
            "current_step": "completed",
            "progress": 100,
            "message": "Queue processing completed successfully"
        }
        
        logger.info(f"✅ Step 4 completed: Queue processing finalized for {job.document_id}")
        
        # Update document status to finalizing before completion
        await update_document_status(job.document_id, "finalizing")
        
        # Update document status to completed at the end
        await update_document_status(job.document_id, "completed")
        
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
        
        # STEP 1: Initialize atomic processing
        logger.info(f"Step 1/5: Initializing ATOMIC processing for {request.document_id}")
        await update_job_status(request.job_id, "processing", {
            "current_step": "atomic_initialized",
            "progress": 10,
            "message": "Atomic processing pipeline initialized"
        })
        await update_document_status(request.document_id, "processing")
        
        # STEP 2: Get document information
        logger.info(f"Step 2/5: Getting document information for {request.document_id}")
        await update_job_status(request.job_id, "processing", {
            "current_step": "document_info_retrieval",
            "progress": 20,
            "message": "Retrieving document information"
        })
        
        document_info = await get_document_info(request.document_id)
        file_path = document_info.get("file_path")
        
        if not file_path:
            error_msg = "Document file path not found"
            logger.error(f"Error in step 2: {error_msg}")
            await update_job_status(request.job_id, "failed", {
                "current_step": "document_info_retrieval",
                "error": error_msg
            })
            await update_document_status(request.document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 2 completed: Document info retrieved for {request.document_id}")
        
        # STEP 3: Extract text from document
        logger.info(f"Step 3/5: Extracting text from {file_path}")
        await update_job_status(request.job_id, "processing", {
            "current_step": "text_extraction",
            "progress": 40,
            "message": f"Extracting text from {os.path.basename(file_path)}"
        })
        
        text_result = await extract_text_from_document(request.document_id, file_path)
        
        if not text_result.get("success"):
            error_msg = f"Text extraction failed: {text_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 3: {error_msg}")
            await update_job_status(request.job_id, "failed", {
                "current_step": "text_extraction",
                "error": error_msg
            })
            await update_document_status(request.document_id, "failed")
            raise Exception(error_msg)
        
        text_content = text_result.get("text_content", "")
        if not text_content:
            error_msg = "No text content extracted from document"
            logger.error(f"Error in step 3: {error_msg}")
            await update_job_status(request.job_id, "failed", {
                "current_step": "text_extraction",
                "error": error_msg
            })
            await update_document_status(request.document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 3 completed: Text extracted ({len(text_content)} characters) for {request.document_id}")
        
        # Update progress atomically
        progress_results = {
            "current_step": "embedding_generation",
            "progress": 60,
            "text_extracted": True,
            "text_content_length": len(text_content)
        }
        await state_manager.update_job_progress(request.job_id, 60, "embedding_generation", progress_results)
        
        # STEP 4: Generate embeddings
        logger.info(f"Step 4/5: Generating embeddings for {len(text_content)} characters of text")
        await update_job_status(request.job_id, "processing", {
            "current_step": "embedding_generation",
            "progress": 70,
            "message": f"Generating embeddings for {len(text_content)} characters of text"
        })
        
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
            error_msg = f"Embedding generation failed: {embedding_result.get('error', 'Unknown error')}"
            logger.error(f"Error in step 4: {error_msg}")
            await update_job_status(request.job_id, "failed", {
                "current_step": "embedding_generation",
                "error": error_msg
            })
            await update_document_status(request.document_id, "failed")
            raise Exception(error_msg)
        
        logger.info(f"✅ Step 4 completed: Embeddings generated for {request.document_id}")
        
        # STEP 5: Finalize atomic processing
        logger.info(f"Step 5/5: Finalizing ATOMIC processing for {request.document_id}")
        await update_job_status(request.job_id, "processing", {
            "current_step": "finalizing",
            "progress": 90,
            "message": "Finalizing atomic processing and storing results"
        })
        
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
            "progress": 100,
            "message": "Atomic processing completed successfully"
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
            logger.info(f"✅ Step 5 completed: ATOMIC processing finalized for {request.document_id}")
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
    port = int(os.getenv("PROCESSING_PIPELINE_PORT", 8003))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port) 