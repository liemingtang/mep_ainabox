#!/usr/bin/env python3
"""
Text Processor - Document text extraction service
"""

import asyncio
import os
import sys
import httpx
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Text Processor",
    description="Document text extraction service for MDIS",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")

# Request/Response models
class ExtractTextRequest(BaseModel):
    document_path: str
    document_id: Optional[str] = None
    host_scan_folder_path: Optional[str] = None

class ExtractTextResponse(BaseModel):
    document_id: Optional[str]
    success: bool
    text_content: str
    text_length: int
    quality_score: float
    extracted_tables: list
    layout_info: dict
    file_path: str

async def update_job_status(document_id: str, status: str, result_data: Dict[str, Any] = None):
    """Update job status in the processing pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PROCESSING_PIPELINE_URL}/jobs/{document_id}/status",
                json={
                    "status": status,
                    "result_data": result_data or {}
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Updated job status for document {document_id} to {status}")
    except Exception as e:
        logger.warning(f"Failed to update job status for document {document_id}: {e}")

def get_shared_volume_path(container_path: str) -> str:
    """Convert container path to native file system path"""
    try:
        # If the path is already a native path, return it
        if not container_path.startswith('/app/'):
            return container_path
        
        # If it's a scan folder path, convert to native path
        if container_path.startswith('/app/scan_folder/'):
            # Extract the filename from the container path
            filename = Path(container_path).name
            # Try to find the file in the watch folder
            watch_folder = os.getenv("WATCH_FOLDER_PATH", "/media/lie/DATA2/ai_scan_folder")
            native_path = f"{watch_folder}/{filename}"
            if Path(native_path).exists():
                logger.info(f"Found file in watch folder: {native_path}")
                return native_path
            
            # If not found, try the default ai_scan_folder path
            default_path = f"/media/lie/DATA2/ai_scan_folder/{filename}"
            logger.info(f"Converted container path {container_path} to native path {default_path}")
            return default_path
        
        # If it's already a shared volume path, convert to native path
        if container_path.startswith('/app/scan_folders/'):
            return container_path
        
        # For other container paths, try to find them in shared volume
        filename = Path(container_path).name
        # Try common folder names in shared volume
        for folder_name in ['ai_scan_folder', 'documents', 'watch_folder']:
            shared_path = f"/app/scan_folders/{folder_name}/{filename}"
            if Path(shared_path).exists():
                logger.info(f"Found file in shared volume: {shared_path}")
                return shared_path
        
        # Fallback to original path
        logger.warning(f"Could not find file in shared volume for {container_path}, using original path")
        return container_path
        
    except Exception as e:
        logger.warning(f"Error converting to shared volume path {container_path}: {e}")
        return container_path

def _get_mounted_folders() -> List[str]:
    """Get list of mounted folders in native file system"""
    try:
        # Use the watch folder path from environment
        watch_folder = os.getenv("WATCH_FOLDER_PATH", "/media/lie/DATA2/ai_scan_folder")
        watch_path = Path(watch_folder)
        if watch_path.exists():
            return [watch_path.name]
        return []
    except Exception as e:
        logger.warning(f"Error getting mounted folders: {e}")
        return []

def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file types with dynamic folder mounting support"""
    try:
        import time
        original_file_path = file_path
        file_path = Path(file_path)
        
        logger.info(f"=== EXTRACT_TEXT_FROM_FILE CALLED at {time.time()} ===")
        logger.info(f"Original file path: {original_file_path}")
        logger.info(f"File path: {file_path}")
        logger.info(f"File exists: {file_path.exists()}")
        
        # If file doesn't exist and it's a container path, try to get the native path
        if not file_path.exists() and str(file_path).startswith('/app/scan_folder/'):
            native_path = get_shared_volume_path(str(file_path))
            if native_path != str(file_path):
                logger.info(f"Trying native path: {native_path}")
                file_path = Path(native_path)
                logger.info(f"Native file exists: {file_path.exists()}")
        
        # Also try to resolve any /app/scan_folders paths to native paths
        if not file_path.exists() and str(file_path).startswith('/app/scan_folders/'):
            # Extract filename and try to find it in the watch folder
            filename = file_path.name
            watch_folder = os.getenv("WATCH_FOLDER_PATH", "/media/lie/DATA2/ai_scan_folder")
            native_path = f"{watch_folder}/{filename}"
            logger.info(f"Trying native path for scan folder file: {native_path}")
            file_path = Path(native_path)
            logger.info(f"Native scan folder file exists: {file_path.exists()}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        file_extension = file_path.suffix.lower()
        logger.info(f"File extension: {file_extension}")
        
        # Handle different file types
        if file_extension in ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm']:
            # Text-based files - read directly
            logger.info(f"Reading text file: {file_path}")
            logger.info(f"File size before reading: {file_path.stat().st_size}")
            logger.info(f"Absolute file path: {file_path.absolute()}")
            logger.info(f"File path exists: {file_path.exists()}")
            logger.info(f"File path is file: {file_path.is_file()}")
            logger.info(f"File path is readable: {file_path.is_file() and os.access(file_path, os.R_OK)}")
            
            # Try to detect file encoding
            import chardet
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    logger.info(f"Detected encoding: {detected}")
                    logger.info(f"Confidence: {detected['confidence']}")
                    logger.info(f"Language: {detected['language']}")
            except Exception as e:
                logger.info(f"Could not detect encoding: {e}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                logger.info(f"File handle opened successfully")
                logger.info(f"File handle position before read: {f.tell()}")
                content = f.read()
                logger.info(f"File handle position after read: {f.tell()}")
                logger.info(f"Read operation completed")
            
            logger.info(f"Raw content length: {len(content)}")
            logger.info(f"Raw content: {repr(content)}")
            logger.info(f"Text content length: {len(content)}")
            logger.info(f"Text content preview: {content[:100]}...")
            logger.info(f"About to return content with length: {len(content)}")
            result = content
            logger.info(f"Returning result with length: {len(result)}")
            return result
            
        elif file_extension in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs', '.swift', '.kt']:
            # Source code files - read as text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
            
        elif file_extension in ['.log', '.out', '.err']:
            # Log files - read as text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
            
        elif file_extension == '.pdf':
            # PDF files - use PyPDF2 for text extraction
            logger.info(f"Processing PDF file: {file_path}")
            try:
                import PyPDF2
                text_content = ""
                
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    logger.info(f"PDF has {len(pdf_reader.pages)} pages")
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                                logger.info(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                            else:
                                logger.warning(f"No text extracted from page {page_num + 1}")
                        except Exception as e:
                            logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                            text_content += f"\n--- Page {page_num + 1} ---\n[Error extracting text: {e}]\n"
                
                if not text_content.strip():
                    logger.warning("No text content extracted from PDF")
                    return "[PDF file with no extractable text content]"
                
                logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
                return text_content
                
            except ImportError:
                logger.error("PyPDF2 not available for PDF processing")
                return "[PDF processing not available - PyPDF2 not installed]"
            except Exception as e:
                logger.error(f"Error processing PDF {file_path}: {e}")
                return f"[Error processing PDF: {e}]"
            
        elif file_extension in ['.docx', '.doc']:
            # Word documents - use python-docx
            logger.info(f"Processing Word document: {file_path}")
            try:
                from docx import Document
                doc = Document(file_path)
                text_content = ""
                
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_content += paragraph.text + "\n"
                
                logger.info(f"Successfully extracted {len(text_content)} characters from Word document")
                return text_content
                
            except ImportError:
                logger.error("python-docx not available for Word document processing")
                return "[Word document processing not available - python-docx not installed]"
            except Exception as e:
                logger.error(f"Error processing Word document {file_path}: {e}")
                return f"[Error processing Word document: {e}]"
            
        else:
            # For other file types, try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            except UnicodeDecodeError:
                # If UTF-8 fails, try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        return content
                    except UnicodeDecodeError:
                        continue
                
                # If all encodings fail, return a placeholder
                return f"[Binary or unsupported file type: {file_extension}]"
                
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "text-processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Text Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL
    }

@app.post("/extract-text")
async def extract_text(request: ExtractTextRequest):
    """Extract text from document"""
    try:
        logger.info(f"Extracting text from {request.document_path}")
        
        # Extract text from file
        text_content = extract_text_from_file(request.document_path)
        
        # Calculate quality metrics
        text_length = len(text_content)
        quality_score = min(1.0, text_length / 1000.0)  # Simple quality score based on length
        
        result = ExtractTextResponse(
            document_id=request.document_id,
            success=True,
            text_content=text_content,
            text_length=text_length,
            quality_score=quality_score,
            extracted_tables=[],  # Not implemented yet
            layout_info={},       # Not implemented yet
            file_path=request.document_path
        )
        
        logger.info(f"Text extraction completed: {text_length} characters extracted")
        return result
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(e)}"
        )

@app.post("/process")
async def process_document(request: Dict[str, Any]):
    """Process document from processing pipeline"""
    try:
        document_id = request.get("document_id")
        document_path = request.get("document_path")
        
        if not document_id or not document_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing document_id or document_path"
            )
        
        logger.info(f"Processing document {document_id} from {document_path}")
        
        # Extract text from file
        text_content = extract_text_from_file(document_path)
        text_length = len(text_content)
        quality_score = min(1.0, text_length / 1000.0)
        
        # Update job status to completed with all processing steps
        result_data = {
            "text_extracted": True,
            "text_content": text_content,
            "text_length": text_length,
            "quality_score": quality_score,
            "entities_extracted": False,  # Not implemented yet
            "metadata_extracted": True,
            "embeddings_generated": False,  # Will be done by embedding processor
            "relationships_mapped": False,  # Not implemented yet
            "processing_time": 2.0,
            "file_path": document_path
        }
        
        # Update job status to completed
        await update_job_status(document_id, "completed", result_data)
        
        logger.info(f"Text processing completed for document {document_id}: {text_length} characters")
        
        return {
            "document_id": document_id,
            "success": True,
            "message": "Text extraction completed",
            "result": {
                "text_content": text_content,
                "text_length": text_length,
                "quality_score": quality_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        
        # Update job status to failed
        await update_job_status(document_id, "failed", {"error": str(e)})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("TEXT_PROCESSOR_PORT", 8005))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    ) 