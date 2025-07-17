#!/usr/bin/env python3
"""
Embedding Processor - Vector embedding generation and storage service using Ollama
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Embedding Processor",
    description="Vector embedding generation and storage service using Ollama",
    version="2.0.0"
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
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "qdrant_api_key")

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Request/Response models
class EmbeddingRequest(BaseModel):
    document_id: str
    text_content: str
    metadata: Optional[Dict[str, Any]] = None
    model: Optional[str] = None  # Allow specifying different Ollama models

class EmbeddingResponse(BaseModel):
    document_id: str
    status: str
    embeddings_count: int
    vector_dimensions: int
    model_used: str
    stored_in_qdrant: bool
    processing_time: float

class EmbeddingQueryRequest(BaseModel):
    text: str
    model: Optional[str] = None
    limit: Optional[int] = 10

class EmbeddingQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    model_used: str

class TextChunker:
    """Split text into chunks for embedding generation"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_endings = ['.', '!', '?', '\n\n']
                for ending in sentence_endings:
                    last_ending = text.rfind(ending, start, end)
                    if last_ending > start:
                        end = last_ending + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks

class OllamaEmbeddingGenerator:
    """Generate embeddings using Ollama models"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.default_model = DEFAULT_EMBEDDING_MODEL
        self.model_dimensions = {
            "nomic-embed-text": 768,
            "all-minilm": 384,
            "all-mpnet-base-v2": 768,
            "text-embedding-ada-002": 1536,
            "e5-large-v2": 1024,
            "e5-base-v2": 768,
            "e5-small-v2": 384
        }
    
    async def check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                response.raise_for_status()
                
                models = response.json().get("models", [])
                available_models = [model["name"] for model in models]
                
                return model_name in available_models
                
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model to Ollama if not available"""
        try:
            logger.info(f"Pulling model {model_name} to Ollama...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    timeout=300.0  # Longer timeout for model pulling
                )
                response.raise_for_status()
                logger.info(f"Successfully pulled model {model_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def generate_embeddings(self, texts: List[str], model_name: str = None) -> List[List[float]]:
        """Generate embeddings for a list of texts using Ollama"""
        model = model_name or self.default_model
        
        try:
            # Check if model is available
            if not await self.check_model_availability(model):
                logger.info(f"Model {model} not available, attempting to pull...")
                if not await self.pull_model(model):
                    raise Exception(f"Failed to pull model {model}")
            
            logger.info(f"Generating embeddings using Ollama model: {model}")
            
            embeddings = []
            async with httpx.AsyncClient() as client:
                for text in texts:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": model,
                            "prompt": text
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    embedding = data.get("embedding", [])
                    
                    if not embedding:
                        raise Exception(f"No embedding returned for text: {text[:100]}...")
                    
                    embeddings.append(embedding)
            
            logger.info(f"Generated {len(embeddings)} embeddings using model {model}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings with Ollama: {e}")
            raise
    
    def get_model_dimensions(self, model_name: str) -> int:
        """Get the expected dimensions for a model"""
        return self.model_dimensions.get(model_name, 768)  # Default to 768
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List available models in Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                response.raise_for_status()
                
                models = response.json().get("models", [])
                return [
                    {
                        "name": model["name"],
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                        "dimensions": self.get_model_dimensions(model["name"])
                    }
                    for model in models
                ]
                
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

class QdrantClient:
    """Client for interacting with Qdrant vector database"""
    
    def __init__(self, host: str = "qdrant", port: int = 6333, api_key: str = "qdrant_api_key"):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
        self.collection_name = "document_embeddings"
        self.headers = {"api-key": api_key} if api_key else {}
    
    async def create_collection(self, dimensions: int = 768) -> bool:
        """Create the embeddings collection if it doesn't exist"""
        try:
            async with httpx.AsyncClient() as client:
                # Check if collection exists
                response = await client.get(
                    f"{self.base_url}/collections/{self.collection_name}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return True
                
                # Create collection
                create_response = await client.put(
                    f"{self.base_url}/collections/{self.collection_name}",
                    headers=self.headers,
                    json={
                        "vectors": {
                            "size": dimensions,
                            "distance": "Cosine"
                        }
                    },
                    timeout=10.0
                )
                
                if create_response.status_code == 200:
                    logger.info(f"Created collection {self.collection_name} with {dimensions} dimensions")
                    return True
                else:
                    logger.error(f"Failed to create collection: {create_response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False
    
    async def store_embeddings(self, document_id: str, embeddings: List[List[float]], 
                             texts: List[str], metadata: Dict[str, Any] = None, model_name: str = None) -> bool:
        """Store embeddings in Qdrant"""
        try:
            # Ensure collection exists with correct dimensions
            dimensions = len(embeddings[0]) if embeddings else 768
            await self.create_collection(dimensions)
            
            # Prepare points for insertion
            points = []
            for i, (embedding, text) in enumerate(zip(embeddings, texts)):
                # Generate a unique integer ID based on document_id and chunk index
                import hashlib
                id_string = f"{document_id}_{i}"
                point_id = int(hashlib.md5(id_string.encode()).hexdigest()[:8], 16)
                
                point = {
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": text[:1000],  # Limit text length
                        "text_length": len(text),
                        "metadata": metadata or {},
                        "model_used": model_name or DEFAULT_EMBEDDING_MODEL,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                points.append(point)
            
            # Insert points
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/collections/{self.collection_name}/points",
                    headers=self.headers,
                    json={"points": points},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Stored {len(points)} embeddings for document {document_id}")
                    return True
                else:
                    logger.error(f"Failed to store embeddings: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return False
    
    async def search_similar(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/collections/{self.collection_name}/points/search",
                    headers=self.headers,
                    json={
                        "vector": query_embedding,
                        "limit": limit,
                        "with_payload": True
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()["result"]
                else:
                    logger.error(f"Search failed: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []

# Initialize components
text_chunker = TextChunker()
embedding_generator = OllamaEmbeddingGenerator()
qdrant_client = QdrantClient(QDRANT_HOST, int(QDRANT_PORT), QDRANT_API_KEY)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections", 
                headers={"api-key": QDRANT_API_KEY},
                timeout=5.0
            )
            qdrant_healthy = response.status_code == 200
    except:
        qdrant_healthy = False
    
    try:
        # Check Ollama connection
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            ollama_healthy = response.status_code == 200
    except:
        ollama_healthy = False
    
    return {
        "status": "healthy" if (qdrant_healthy and ollama_healthy) else "degraded",
        "service": "embedding-processor",
        "qdrant_connection": "healthy" if qdrant_healthy else "unhealthy",
        "ollama_connection": "healthy" if ollama_healthy else "unhealthy",
        "default_model": DEFAULT_EMBEDDING_MODEL,
        "ollama_url": OLLAMA_BASE_URL
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Embedding Processor with Ollama",
        "version": "2.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL,
        "core_processor": CORE_PROCESSOR_URL,
        "qdrant_host": QDRANT_HOST,
        "ollama_url": OLLAMA_BASE_URL,
        "default_model": DEFAULT_EMBEDDING_MODEL,
        "endpoints": {
            "health": "/health",
            "process": "/process",
            "search": "/search",
            "models": "/models",
            "embed": "/embed"
        }
    }

@app.post("/process")
async def process_embeddings(request: EmbeddingRequest):
    """Process document embeddings"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Processing embeddings for document {request.document_id}")
        
        # Chunk the text
        text_chunks = text_chunker.chunk_text(request.text_content)
        logger.info(f"Created {len(text_chunks)} text chunks for document {request.document_id}")
        
        # Generate embeddings
        model_name = request.model or DEFAULT_EMBEDDING_MODEL
        embeddings = await embedding_generator.generate_embeddings(text_chunks, model_name)
        logger.info(f"Generated {len(embeddings)} embeddings for document {request.document_id}")
        
        # Store in Qdrant
        stored = await qdrant_client.store_embeddings(
            request.document_id,
            embeddings,
            text_chunks,
            request.metadata,
            model_name
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Update job status in processing pipeline
        result_data = {
            "embeddings_count": len(embeddings),
            "vector_dimensions": len(embeddings[0]) if embeddings else 0,
            "model_used": model_name,
            "stored_in_qdrant": stored,
            "processing_time": processing_time,
            "text_chunks": len(text_chunks),
            "average_chunk_length": sum(len(chunk) for chunk in text_chunks) / len(text_chunks) if text_chunks else 0
        }
        
        await update_job_status(request.document_id, "completed", result_data)
        
        logger.info(f"Embedding processing completed for document {request.document_id}")
        
        return EmbeddingResponse(
            document_id=request.document_id,
            status="completed",
            embeddings_count=len(embeddings),
            vector_dimensions=len(embeddings[0]) if embeddings else 0,
            model_used=model_name,
            stored_in_qdrant=stored,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing embeddings for document {request.document_id}: {e}")
        
        # Update job status to failed
        await update_job_status(request.document_id, "failed", {"error": str(e)})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing embeddings: {str(e)}"
        )

@app.post("/search")
async def search_embeddings(request: EmbeddingQueryRequest):
    """Search for similar documents"""
    try:
        model_name = request.model or DEFAULT_EMBEDDING_MODEL
        
        # Generate embedding for query
        query_embeddings = await embedding_generator.generate_embeddings([request.text], model_name)
        query_embedding = query_embeddings[0]
        
        # Search in Qdrant
        results = await qdrant_client.search_similar(query_embedding, request.limit)
        
        return EmbeddingQueryResponse(
            query=request.text,
            results=results,
            total_found=len(results),
            model_used=model_name
        )
        
    except Exception as e:
        logger.error(f"Error searching embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching embeddings: {str(e)}"
        )

@app.post("/embed")
async def generate_single_embedding(text: str, model: str = None):
    """Generate a single embedding for a text (useful for external services like n8n)"""
    try:
        model_name = model or DEFAULT_EMBEDDING_MODEL
        embeddings = await embedding_generator.generate_embeddings([text], model_name)
        
        return {
            "text": text,
            "embedding": embeddings[0],
            "dimensions": len(embeddings[0]),
            "model_used": model_name
        }
        
    except Exception as e:
        logger.error(f"Error generating single embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating embedding: {str(e)}"
        )

@app.get("/models")
async def list_available_models():
    """List available embedding models"""
    try:
        ollama_models = await embedding_generator.list_available_models()
        
        return {
            "default_model": DEFAULT_EMBEDDING_MODEL,
            "ollama_models": ollama_models,
            "recommended_models": [
                "nomic-embed-text",  # 768 dimensions, high quality
                "all-minilm",  # 384 dimensions, fast
                "all-mpnet-base-v2",  # 768 dimensions, high quality
                "e5-large-v2",  # 1024 dimensions, excellent quality
                "e5-base-v2",  # 768 dimensions, good quality
                "e5-small-v2"  # 384 dimensions, fast
            ]
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {
            "default_model": DEFAULT_EMBEDDING_MODEL,
            "ollama_models": [],
            "error": str(e)
        }

@app.post("/api/v1/process")
async def process_embeddings_legacy():
    """Legacy endpoint for backward compatibility"""
    return {
        "status": "processed",
        "embeddings": {
            "count": 1,
            "dimensions": 768,
            "model": DEFAULT_EMBEDDING_MODEL
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
        port=8007,
        reload=False,
        log_level="info"
    ) 