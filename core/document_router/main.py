from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import os
import json
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MDIS Document Router", version="1.0.0")

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
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://processing-pipeline:8003")

# Request/Response models
class DocumentAnalysisRequest(BaseModel):
    document_id: str
    document: Dict[str, Any]

class DocumentAnalysisResponse(BaseModel):
    document_id: str
    analysis_status: str
    document_type: str
    processing_priority: str
    recommended_processors: List[str]
    estimated_processing_time: str
    confidence_score: float

class RoutingResponse(BaseModel):
    status: str
    processors: List[str]
    priority: str
    estimated_time: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "document-router"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Document Router",
        "version": "1.0.0",
        "services": {
            "core-processor": CORE_PROCESSOR_URL,
            "processing-pipeline": PROCESSING_PIPELINE_URL
        }
    }

@app.post("/analyze")
async def analyze_document(request: DocumentAnalysisRequest):
    """Analyze a document and determine processing requirements"""
    try:
        logger.info(f"Analyzing document {request.document_id}")
        
        document = request.document
        document_id = request.document_id
        
        # Extract document information
        filename = document.get("filename", "")
        mime_type = document.get("mime_type", "")
        file_size = document.get("file_size", 0)
        document_type = document.get("document_type", "unknown")
        
        # Analyze document type and determine processing requirements
        analysis_result = await analyze_document_type(filename, mime_type, file_size, document_type)
        
        logger.info(f"Analysis completed for document {document_id}: {analysis_result['document_type']}")
        
        return DocumentAnalysisResponse(
            document_id=document_id,
            analysis_status="completed",
            document_type=analysis_result["document_type"],
            processing_priority=analysis_result["priority"],
            recommended_processors=analysis_result["processors"],
            estimated_processing_time=analysis_result["estimated_time"],
            confidence_score=analysis_result["confidence"]
        )
        
    except Exception as e:
        logger.error(f"Error analyzing document {request.document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")

async def analyze_document_type(filename: str, mime_type: str, file_size: int, document_type: str) -> Dict[str, Any]:
    """Analyze document type and determine processing requirements"""
    
    # Default analysis
    analysis = {
        "document_type": "unknown",
        "priority": "normal",
        "processors": ["text_processor", "metadata_processor"],
        "estimated_time": "30 seconds",
        "confidence": 0.5
    }
    
    # Analyze based on file extension
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        analysis.update({
            "document_type": "pdf",
            "processors": ["text_processor", "metadata_processor", "embedding_processor", "entity_processor"],
            "estimated_time": "45 seconds",
            "confidence": 0.9
        })
    elif filename_lower.endswith('.docx'):
        analysis.update({
            "document_type": "docx", 
            "processors": ["text_processor", "metadata_processor", "embedding_processor"],
            "estimated_time": "35 seconds",
            "confidence": 0.8
        })
    elif filename_lower.endswith('.txt'):
        analysis.update({
            "document_type": "txt",
            "processors": ["text_processor", "metadata_processor", "embedding_processor"],
            "estimated_time": "20 seconds", 
            "confidence": 0.9
        })
    elif filename_lower.endswith('.html'):
        analysis.update({
            "document_type": "html",
            "processors": ["text_processor", "metadata_processor", "embedding_processor"],
            "estimated_time": "25 seconds",
            "confidence": 0.8
        })
    elif any(filename_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']):
        analysis.update({
            "document_type": "image",
            "processors": ["image_processor", "ocr_processor", "metadata_processor"],
            "estimated_time": "60 seconds",
            "confidence": 0.7
        })
    
    # Adjust priority based on file size
    if file_size > 10 * 1024 * 1024:  # > 10MB
        analysis["priority"] = "low"
        analysis["estimated_time"] = f"{int(int(analysis['estimated_time'].split()[0]) * 1.5)} seconds"
    elif file_size < 1024 * 1024:  # < 1MB
        analysis["priority"] = "high"
    
    # Adjust based on mime type if available
    if mime_type:
        if "pdf" in mime_type.lower():
            analysis["document_type"] = "pdf"
            analysis["confidence"] = 0.95
        elif "word" in mime_type.lower() or "document" in mime_type.lower():
            analysis["document_type"] = "docx"
            analysis["confidence"] = 0.9
        elif "text" in mime_type.lower():
            analysis["document_type"] = "txt"
            analysis["confidence"] = 0.95
        elif "image" in mime_type.lower():
            analysis["document_type"] = "image"
            analysis["confidence"] = 0.8
    
    return analysis

@app.post("/api/v1/route")
async def route_document():
    """Route a document to appropriate processors"""
    try:
        # Basic routing logic - in a real implementation, this would analyze the document
        # and determine which processors to use
        return RoutingResponse(
            status="routed",
            processors=["text-processor", "metadata-processor", "embedding-processor"],
            priority="normal",
            estimated_time="30 seconds"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error routing document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 