#!/usr/bin/env python3
"""
Text Processor - Document text extraction service
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.logging import setup_logging
from app.services.text_extraction_service import TextExtractionService

# Setup logging
logger = setup_logging()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = asyncio.get_event_loop().time()
        
        response = await call_next(request)
        
        duration = asyncio.get_event_loop().time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.observe(duration)
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Text Processor service...")
    
    # Initialize services
    app.state.text_extraction_service = TextExtractionService()
    
    logger.info("Text Processor service started successfully")
    
    yield
    
    logger.info("Shutting down Text Processor service...")

# Create FastAPI application
app = FastAPI(
    title="Text Processor",
    description="Document text extraction service for MDIS",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "text-processor"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/extract-text")
async def extract_text(document_path: str, document_id: str):
    """Extract text from document"""
    try:
        logger.info(f"Extracting text from document: {document_path}")
        
        # Extract text
        result = await app.state.text_extraction_service.extract_text(document_path)
        
        # Store result
        await app.state.text_extraction_service.store_result(document_id, result)
        
        return {
            "document_id": document_id,
            "success": True,
            "text_content": result["text_content"],
            "extracted_tables": result["extracted_tables"],
            "layout_info": result["layout_info"],
            "quality_score": result["quality_score"]
        }
        
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
        
        logger.info(f"Processing document: {document_id}")
        
        # Extract text
        result = await app.state.text_extraction_service.extract_text(document_path)
        
        # Store result
        await app.state.text_extraction_service.store_result(document_id, result)
        
        # Notify processing pipeline
        await app.state.text_extraction_service.notify_completion(document_id, result)
        
        return {
            "document_id": document_id,
            "success": True,
            "message": "Text extraction completed"
        }
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("API_PORT", 8005))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting Text Processor on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="INFO"
    ) 