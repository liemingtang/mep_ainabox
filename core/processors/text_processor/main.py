#!/usr/bin/env python3
"""
Text Processor - Document text extraction service
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://processing-pipeline:8003")

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
async def extract_text(document_path: str, document_id: str):
    """Extract text from document"""
    try:
        # Basic text extraction - in a real implementation, this would extract
        # text from various document formats
        return {
            "document_id": document_id,
            "success": True,
            "text_content": f"Extracted text from {document_path}",
            "extracted_tables": [],
            "layout_info": {},
            "quality_score": 0.95
        }
        
    except Exception as e:
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
        
        # Basic text extraction
        result = {
            "text_content": f"Extracted text from {document_path}",
            "extracted_tables": [],
            "layout_info": {},
            "quality_score": 0.95
        }
        
        return {
            "document_id": document_id,
            "success": True,
            "message": "Text extraction completed",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("API_PORT", 8005))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    ) 