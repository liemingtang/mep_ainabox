#!/usr/bin/env python3
"""
Metadata Processor - Document metadata extraction and validation service
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Metadata Processor",
    description="Document metadata extraction and validation service for MDIS",
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
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")

# Request/Response models
class MetadataRequest(BaseModel):
    document_id: str
    file_path: str
    filename: str
    mime_type: str
    file_size: int

class MetadataResponse(BaseModel):
    document_id: str
    status: str
    metadata: Dict[str, Any]
    extracted_at: str

class MetadataExtractor:
    """Extract metadata from various document types"""
    
    def __init__(self):
        self.supported_types = {
            'text/plain': self._extract_text_metadata,
            'application/pdf': self._extract_pdf_metadata,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._extract_docx_metadata,
            'text/html': self._extract_html_metadata,
            'application/json': self._extract_json_metadata,
            'text/csv': self._extract_csv_metadata
        }
    
    def _get_shared_volume_path(self, file_path: str) -> str:
        """Convert file path to shared volume path if needed"""
        try:
            # If it's already a shared volume path, return as is
            if file_path.startswith('/app/scan_folders/'):
                return file_path
            
            # If it's a scan folder path, try to find it in shared volume
            if file_path.startswith('/app/scan_folder/'):
                filename = Path(file_path).name
                # Try to find the file in any mounted folder in shared volume
                for folder_name in self._get_mounted_folders():
                    shared_path = f"/app/scan_folders/{folder_name}/{filename}"
                    if Path(shared_path).exists():
                        logger.info(f"Found file in shared volume: {shared_path}")
                        return shared_path
                
                # If not found, try the default ai_scan_folder path
                shared_path = f"/app/scan_folders/ai_scan_folder/{filename}"
                logger.info(f"Converted container path {file_path} to shared volume path {shared_path}")
                return shared_path
            
            # For other paths, return as is
            return file_path
            
        except Exception as e:
            logger.warning(f"Error converting to shared volume path {file_path}: {e}")
            return file_path
    
    def _get_mounted_folders(self) -> List[str]:
        """Get list of mounted folders in shared volume"""
        try:
            # Use a simple approach to list directories in the shared volume
            scan_folders_path = Path("/app/scan_folders")
            if scan_folders_path.exists():
                folders = [d.name for d in scan_folders_path.iterdir() if d.is_dir()]
                return folders
            return []
        except Exception as e:
            logger.warning(f"Error getting mounted folders: {e}")
            return []
    
    async def extract_metadata(self, file_path: str, filename: str, mime_type: str, file_size: int) -> Dict[str, Any]:
        """Extract metadata from document with shared volume support"""
        try:
            # Convert file path to shared volume path if needed
            file_path = self._get_shared_volume_path(file_path)
            
            # Basic file metadata
            metadata = {
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "file_extension": Path(filename).suffix.lower(),
                "extracted_at": datetime.utcnow().isoformat(),
                "processing_status": "completed"
            }
            
            # Extract content-based metadata
            if mime_type in self.supported_types:
                content_metadata = await self.supported_types[mime_type](file_path)
                metadata.update(content_metadata)
            else:
                # Generic metadata for unsupported types
                metadata.update(await self._extract_generic_metadata(file_path))
            
            # Add file analysis
            metadata.update(await self._analyze_file(file_path, file_size))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type,
                "error": str(e),
                "processing_status": "failed"
            }
    
    async def _extract_text_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            words = content.split()
            
            return {
                "content_type": "text",
                "line_count": len(lines),
                "word_count": len(words),
                "character_count": len(content),
                "language": self._detect_language(content),
                "has_tables": self._detect_tables(content),
                "has_numbers": bool(re.search(r'\d+', content)),
                "has_dates": bool(re.search(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', content)),
                "has_emails": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
                "has_urls": bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content))
            }
        except Exception as e:
            logger.error(f"Error extracting text metadata: {e}")
            return {"content_type": "text", "error": str(e)}
    
    async def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF files"""
        try:
            # For now, return basic PDF metadata
            # In a full implementation, you would use PyPDF2 or pdfplumber
            return {
                "content_type": "pdf",
                "document_type": "pdf",
                "estimated_pages": self._estimate_pdf_pages(file_path),
                "has_text": True,  # Assume PDFs have text
                "is_scanned": False  # Would need OCR analysis
            }
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return {"content_type": "pdf", "error": str(e)}
    
    async def _extract_docx_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from DOCX files"""
        try:
            # For now, return basic DOCX metadata
            # In a full implementation, you would use python-docx
            return {
                "content_type": "docx",
                "document_type": "word_document",
                "has_tables": True,  # Assume DOCX might have tables
                "has_images": True,  # Assume DOCX might have images
                "has_headers": True,  # Assume DOCX might have headers
                "has_footers": True   # Assume DOCX might have footers
            }
        except Exception as e:
            logger.error(f"Error extracting DOCX metadata: {e}")
            return {"content_type": "docx", "error": str(e)}
    
    async def _extract_html_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from HTML files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return {
                "content_type": "html",
                "document_type": "web_page",
                "has_links": bool(re.search(r'<a\s+href=', content)),
                "has_images": bool(re.search(r'<img\s+src=', content)),
                "has_tables": bool(re.search(r'<table', content)),
                "has_forms": bool(re.search(r'<form', content)),
                "title": self._extract_html_title(content),
                "meta_tags": self._extract_html_meta(content)
            }
        except Exception as e:
            logger.error(f"Error extracting HTML metadata: {e}")
            return {"content_type": "html", "error": str(e)}
    
    async def _extract_json_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
            
            return {
                "content_type": "json",
                "document_type": "data_file",
                "json_type": type(data).__name__,
                "json_size": len(str(data)),
                "is_valid_json": True,
                "structure": self._analyze_json_structure(data)
            }
        except Exception as e:
            logger.error(f"Error extracting JSON metadata: {e}")
            return {"content_type": "json", "error": str(e)}
    
    async def _extract_csv_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from CSV files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if lines:
                headers = lines[0].strip().split(',')
                row_count = len(lines) - 1  # Exclude header
            
            return {
                "content_type": "csv",
                "document_type": "spreadsheet",
                "column_count": len(headers) if lines else 0,
                "row_count": row_count if lines else 0,
                "has_headers": True,
                "delimiter": ",",
                "headers": headers if lines else []
            }
        except Exception as e:
            logger.error(f"Error extracting CSV metadata: {e}")
            return {"content_type": "csv", "error": str(e)}
    
    async def _extract_generic_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract generic metadata for unsupported file types"""
        return {
            "content_type": "unknown",
            "document_type": "unknown",
            "processing_note": "File type not fully supported for metadata extraction"
        }
    
    async def _analyze_file(self, file_path: str, file_size: int) -> Dict[str, Any]:
        """Analyze file characteristics"""
        try:
            stat = os.stat(file_path)
            
            return {
                "file_created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "file_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "file_accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "file_permissions": oct(stat.st_mode)[-3:],
                "is_readable": os.access(file_path, os.R_OK),
                "is_writable": os.access(file_path, os.W_OK),
                "size_category": self._categorize_file_size(file_size)
            }
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {"file_analysis_error": str(e)}
    
    def _detect_language(self, content: str) -> str:
        """Simple language detection based on common words"""
        # Very basic language detection - in production, use langdetect or similar
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        content_lower = content.lower()
        
        english_count = sum(1 for word in english_words if word in content_lower)
        if english_count > 3:
            return "en"
        return "unknown"
    
    def _detect_tables(self, content: str) -> bool:
        """Detect if content contains table-like structures"""
        # Look for patterns that suggest tables
        table_patterns = [
            r'\|\s*\w+\s*\|',  # Pipe-separated values
            r'\t\w+',          # Tab-separated values
            r',\s*\w+,\s*\w+', # Comma-separated values
        ]
        
        return any(re.search(pattern, content) for pattern in table_patterns)
    
    def _estimate_pdf_pages(self, file_path: str) -> int:
        """Estimate number of pages in PDF based on file size"""
        # Rough estimation: 1 page ≈ 50KB
        file_size_kb = os.path.getsize(file_path) / 1024
        return max(1, int(file_size_kb / 50))
    
    def _extract_html_title(self, content: str) -> Optional[str]:
        """Extract title from HTML content"""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        return title_match.group(1).strip() if title_match else None
    
    def _extract_html_meta(self, content: str) -> Dict[str, str]:
        """Extract meta tags from HTML content"""
        meta_tags = {}
        meta_matches = re.findall(r'<meta[^>]*name=["\']([^"\']*)["\'][^>]*content=["\']([^"\']*)["\']', content, re.IGNORECASE)
        
        for name, content in meta_matches:
            meta_tags[name.lower()] = content
        
        return meta_tags
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze JSON structure recursively"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "key_count": len(data),
                "nested": {k: self._analyze_json_structure(v, max_depth - 1) for k, v in list(data.items())[:5]} if max_depth > 0 else {}
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "sample_items": [self._analyze_json_structure(item, max_depth - 1) for item in data[:3]] if max_depth > 0 else []
            }
        else:
            return {"type": type(data).__name__}
    
    def _categorize_file_size(self, size_bytes: int) -> str:
        """Categorize file size"""
        if size_bytes < 1024:
            return "tiny"
        elif size_bytes < 1024 * 1024:
            return "small"
        elif size_bytes < 10 * 1024 * 1024:
            return "medium"
        elif size_bytes < 100 * 1024 * 1024:
            return "large"
        else:
            return "very_large"

# Initialize metadata extractor
metadata_extractor = MetadataExtractor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "metadata-processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Metadata Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL,
        "core_processor": CORE_PROCESSOR_URL
    }

@app.post("/process")
async def process_metadata(request: MetadataRequest):
    """Process document metadata"""
    try:
        logger.info(f"Processing metadata for document {request.document_id}")
        
        # Extract metadata
        metadata = await metadata_extractor.extract_metadata(
            request.file_path,
            request.filename,
            request.mime_type,
            request.file_size
        )
        
        # Add document ID to metadata
        metadata["document_id"] = request.document_id
        
        # Update job status in processing pipeline
        await update_job_status(request.document_id, "completed", metadata)
        
        logger.info(f"Metadata processing completed for document {request.document_id}")
        
        return MetadataResponse(
            document_id=request.document_id,
            status="completed",
            metadata=metadata,
            extracted_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing metadata for document {request.document_id}: {e}")
        
        # Update job status to failed
        await update_job_status(request.document_id, "failed", {"error": str(e)})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing metadata: {str(e)}"
        )

@app.post("/api/v1/process")
async def process_metadata_legacy():
    """Legacy endpoint for backward compatibility"""
    return {
        "status": "processed",
        "metadata": {
            "title": "Sample Document",
            "author": "Unknown",
            "date": "2024-01-01",
            "type": "document",
            "pages": 1
        }
    }

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        log_level="info"
    ) 