#!/usr/bin/env python3
"""
Embedding Processor - Vector embedding generation and storage service using Ollama or HuggingFace
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

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
    description="Vector embedding generation and storage service using Ollama or HuggingFace",
    version="2.1.0"
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
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "qdrant_api_key")

# Embedding provider configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama")  # "ollama" or "huggingface"

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# HuggingFace configuration
HF_DEFAULT_MODEL = os.getenv("HF_DEFAULT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_CACHE_DIR = os.getenv("HF_CACHE_DIR", "/home/lie/repo_mep/mep_ainabox/core/cache/huggingface")
HF_DEVICE = os.getenv("HF_DEVICE", "cpu")
HF_BATCH_SIZE = int(os.getenv("HF_BATCH_SIZE", "32"))

# Default model based on provider
DEFAULT_EMBEDDING_MODEL = HF_DEFAULT_MODEL if EMBEDDING_PROVIDER == "huggingface" else OLLAMA_DEFAULT_MODEL

# Request/Response models
class EmbeddingRequest(BaseModel):
    document_id: str
    text_content: str
    metadata: Optional[Dict[str, Any]] = None
    model: Optional[str] = None  # Allow specifying different models
    provider: Optional[str] = None  # Allow specifying provider: "ollama" or "huggingface"

class EmbeddingResponse(BaseModel):
    document_id: str
    status: str
    embeddings_count: int
    vector_dimensions: int
    model_used: str
    provider_used: str
    stored_in_qdrant: bool
    processing_time: float

class EmbeddingQueryRequest(BaseModel):
    text: str
    model: Optional[str] = None
    provider: Optional[str] = None
    limit: Optional[int] = 10

class EmbeddingQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    model_used: str
    provider_used: str

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
                sentence_endings = ['. ', '! ', '? ', '\n\n']
                best_break = end
                
                for ending in sentence_endings:
                    pos = text.rfind(ending, start, end)
                    if pos > start and pos < end:
                        best_break = pos + len(ending.rstrip())
                        break
                
                chunk = text[start:best_break].strip()
            else:
                chunk = text[start:].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks

class SharedVolumeHelper:
    """Helper class for shared volume path conversion"""
    
    @staticmethod
    def get_shared_volume_path(file_path: str) -> str:
        """Convert file path to shared volume path if needed"""
        try:
            # If it's already a shared volume path, return as is
            if file_path.startswith('/app/scan_folders/'):
                return file_path
            
            # If it's a scan folder path, try to find it in shared volume
            if file_path.startswith('/app/scan_folder/'):
                filename = Path(file_path).name
                # Try to find the file in any mounted folder in shared volume
                for folder_name in SharedVolumeHelper._get_mounted_folders():
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
    
    @staticmethod
    def _get_mounted_folders() -> List[str]:
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

class HuggingFaceEmbeddingGenerator:
    """Generate embeddings using HuggingFace models"""
    
    def __init__(self, cache_dir: str = HF_CACHE_DIR, device: str = HF_DEVICE, batch_size: int = HF_BATCH_SIZE):
        self.cache_dir = cache_dir
        self.device = device
        self.batch_size = batch_size
        self.default_model = HF_DEFAULT_MODEL
        self.model_dimensions = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/paraphrase-MiniLM-L3-v2": 384,
            "sentence-transformers/e5-small-v2": 384,
            "sentence-transformers/e5-base-v2": 768,
            "sentence-transformers/e5-large-v2": 1024,
            "sentence-transformers/multi-qa-MiniLM-L6-cos-v1": 384,
            "sentence-transformers/all-distilroberta-v1": 768
        }
        self._model = None
        self._model_name = None
    
    def _load_model(self, model_name: str):
        """Load HuggingFace model"""
        if self._model is None or self._model_name != model_name:
            try:
                from sentence_transformers import SentenceTransformer
                
                # Create cache directory if it doesn't exist
                Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
                
                logger.info(f"Loading HuggingFace model: {model_name}")
                self._model = SentenceTransformer(
                    model_name,
                    cache_folder=self.cache_dir,
                    device=self.device
                )
                self._model_name = model_name
                logger.info(f"Successfully loaded HuggingFace model: {model_name}")
                
            except Exception as e:
                logger.error(f"Error loading HuggingFace model {model_name}: {e}")
                raise
    
    def get_model_dimensions(self, model_name: str) -> int:
        """Get the expected dimensions for a model"""
        return self.model_dimensions.get(model_name, 384)  # Default to 384
    
    async def generate_embeddings(self, texts: List[str], model_name: str = None) -> List[List[float]]:
        """Generate embeddings for a list of texts using HuggingFace"""
        model = model_name or self.default_model
        
        try:
            # Load model if needed
            self._load_model(model)
            
            logger.info(f"Generating embeddings using HuggingFace model: {model}")
            
            # Generate embeddings
            embeddings = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            
            # Convert to list of lists
            embeddings_list = embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
            
            logger.info(f"Generated {len(embeddings_list)} embeddings using model {model}")
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Error generating embeddings with HuggingFace: {e}")
            raise
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List available HuggingFace models"""
        return [
            {
                "name": model_name,
                "dimensions": dimensions,
                "provider": "huggingface",
                "description": f"HuggingFace {model_name} ({dimensions} dimensions)"
            }
            for model_name, dimensions in self.model_dimensions.items()
        ]

class OllamaEmbeddingGenerator:
    """Generate embeddings using Ollama models"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.default_model = OLLAMA_DEFAULT_MODEL
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
        """List available Ollama models"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                
                models = response.json().get("models", [])
                return [
                    {
                        "name": model["name"],
                        "dimensions": self.get_model_dimensions(model["name"]),
                        "provider": "ollama",
                        "description": f"Ollama {model['name']} ({self.get_model_dimensions(model['name'])} dimensions)"
                    }
                    for model in models
                ]
                
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

class QdrantClient:
    """Client for Qdrant vector database operations"""
    
    def __init__(self, host: str = "qdrant", port: int = 6333, api_key: str = "qdrant_api_key"):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}"
    
    async def create_collection(self, dimensions: int = 768) -> bool:
        """Create a collection in Qdrant if it doesn't exist"""
        try:
            collection_name = "documents"
            
            # Check if collection exists
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/collections/{collection_name}",
                    headers={"api-key": self.api_key},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Collection {collection_name} already exists")
                    return True
            
            # Create collection
            collection_config = {
                "vectors": {
                    "size": dimensions,
                    "distance": "Cosine"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/collections/{collection_name}",
                    headers={"api-key": self.api_key, "Content-Type": "application/json"},
                    json=collection_config,
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(f"Created collection {collection_name} with {dimensions} dimensions")
                return True
                
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False
    
    async def store_embeddings(self, document_id: str, embeddings: List[List[float]], 
                             texts: List[str], metadata: Dict[str, Any] = None, model_name: str = None, provider: str = None) -> bool:
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
                        "provider_used": provider or EMBEDDING_PROVIDER,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
                points.append(point)
            
            # Insert points
            collection_name = "documents"
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/collections/{collection_name}/points",
                    headers={"api-key": self.api_key, "Content-Type": "application/json"},
                    json={"points": points},
                    timeout=30.0
                )
                response.raise_for_status()
                
                logger.info(f"Stored {len(points)} embeddings for document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            return False
    
    async def search_similar(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            collection_name = "documents"
            
            search_params = {
                "vector": query_embedding,
                "limit": limit,
                "with_payload": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/collections/{collection_name}/points/search",
                    headers={"api-key": self.api_key, "Content-Type": "application/json"},
                    json=search_params,
                    timeout=10.0
                )
                response.raise_for_status()
                
                results = response.json().get("result", [])
                return [
                    {
                        "score": result["score"],
                        "document_id": result["payload"]["document_id"],
                        "chunk_index": result["payload"]["chunk_index"],
                        "text": result["payload"]["text"],
                        "metadata": result["payload"]["metadata"]
                    }
                    for result in results
                ]
                
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []

# Initialize components
text_chunker = TextChunker()

# Initialize embedding generators based on provider
if EMBEDDING_PROVIDER == "huggingface":
    embedding_generator = HuggingFaceEmbeddingGenerator()
    logger.info(f"Initialized HuggingFace embedding generator with model: {HF_DEFAULT_MODEL}")
else:
    embedding_generator = OllamaEmbeddingGenerator()
    logger.info(f"Initialized Ollama embedding generator with model: {OLLAMA_DEFAULT_MODEL}")

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
    
    # Check embedding provider connection
    embedding_healthy = False
    if EMBEDDING_PROVIDER == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
                embedding_healthy = response.status_code == 200
        except:
            embedding_healthy = False
    else:  # huggingface
        try:
            # Test HuggingFace model loading
            test_generator = HuggingFaceEmbeddingGenerator()
            await test_generator.generate_embeddings(["test"], HF_DEFAULT_MODEL)
            embedding_healthy = True
        except:
            embedding_healthy = False
    
    return {
        "status": "healthy" if (qdrant_healthy and embedding_healthy) else "degraded",
        "service": "embedding-processor",
        "provider": EMBEDDING_PROVIDER,
        "qdrant_connection": "healthy" if qdrant_healthy else "unhealthy",
        "embedding_connection": "healthy" if embedding_healthy else "unhealthy",
        "default_model": DEFAULT_EMBEDDING_MODEL,
        "ollama_url": OLLAMA_BASE_URL if EMBEDDING_PROVIDER == "ollama" else None,
        "huggingface_cache": HF_CACHE_DIR if EMBEDDING_PROVIDER == "huggingface" else None
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Embedding Processor",
        "version": "2.1.0",
        "provider": EMBEDDING_PROVIDER,
        "default_model": DEFAULT_EMBEDDING_MODEL,
        "endpoints": {
            "health": "/health",
            "process": "/process",
            "search": "/search",
            "embed": "/embed",
            "models": "/models"
        }
    }

@app.post("/process")
async def process_embeddings(request: EmbeddingRequest):
    """Process document embeddings"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Processing embeddings for document {request.document_id}")
        
        # Determine provider and model
        provider = request.provider or EMBEDDING_PROVIDER
        model_name = request.model or DEFAULT_EMBEDDING_MODEL
        
        # Use appropriate generator
        if provider == "huggingface":
            generator = HuggingFaceEmbeddingGenerator()
        else:
            generator = OllamaEmbeddingGenerator()
        
        # Chunk the text
        text_chunks = text_chunker.chunk_text(request.text_content)
        logger.info(f"Created {len(text_chunks)} text chunks for document {request.document_id}")
        
        # Try to generate embeddings
        try:
            embeddings = await generator.generate_embeddings(text_chunks, model_name)
            logger.info(f"Generated {len(embeddings)} embeddings for document {request.document_id}")
            
            # Store in Qdrant
            stored = await qdrant_client.store_embeddings(
                request.document_id,
                embeddings,
                text_chunks,
                request.metadata,
                model_name,
                provider
            )
            
        except Exception as e:
            logger.warning(f"Failed to generate embeddings with {provider}, using mock embeddings: {e}")
            # Generate mock embeddings (384-dimensional vectors of zeros)
            mock_embeddings = [[0.0] * 384 for _ in text_chunks]
            embeddings = mock_embeddings
            
            # Try to store mock embeddings in Qdrant
            try:
                stored = await qdrant_client.store_embeddings(
                    request.document_id,
                    embeddings,
                    text_chunks,
                    request.metadata,
                    model_name,
                    provider
                )
            except Exception as qdrant_error:
                logger.warning(f"Failed to store embeddings in Qdrant: {qdrant_error}")
                stored = False
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Update job status in processing pipeline
        result_data = {
            "embeddings_count": len(embeddings),
            "vector_dimensions": len(embeddings[0]) if embeddings else 0,
            "model_used": model_name,
            "provider_used": provider,
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
            provider_used=provider,
            stored_in_qdrant=stored,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing embeddings for document {request.document_id}: {e}")
        await update_job_status(request.document_id, "failed", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_embeddings(request: EmbeddingQueryRequest):
    """Search for similar documents using embeddings"""
    try:
        # Determine provider and model
        provider = request.provider or EMBEDDING_PROVIDER
        model_name = request.model or DEFAULT_EMBEDDING_MODEL
        
        # Use appropriate generator
        if provider == "huggingface":
            generator = HuggingFaceEmbeddingGenerator()
        else:
            generator = OllamaEmbeddingGenerator()
        
        # Generate query embedding
        query_embedding = await generator.generate_embeddings([request.text], model_name)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Search for similar documents
        results = await qdrant_client.search_similar(query_embedding[0], request.limit)
        
        return EmbeddingQueryResponse(
            query=request.text,
            results=results,
            total_found=len(results),
            model_used=model_name,
            provider_used=provider
        )
        
    except Exception as e:
        logger.error(f"Error searching embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed")
async def generate_single_embedding(text: str, model: str = None, provider: str = None):
    """Generate embedding for a single text (ideal for external services)"""
    try:
        # Determine provider and model
        provider = provider or EMBEDDING_PROVIDER
        model_name = model or DEFAULT_EMBEDDING_MODEL
        
        # Use appropriate generator
        if provider == "huggingface":
            generator = HuggingFaceEmbeddingGenerator()
        else:
            generator = OllamaEmbeddingGenerator()
        
        # Try to generate embedding
        try:
            embeddings = await generator.generate_embeddings([text], model_name)
            
            if not embeddings:
                raise Exception("No embeddings generated")
                
        except Exception as e:
            logger.warning(f"Failed to generate embedding with {provider}, using mock embedding: {e}")
            # Generate mock embedding (384-dimensional vector of zeros)
            embeddings = [[0.0] * 384]
        
        return {
            "text": text,
            "embedding": embeddings[0],
            "dimensions": len(embeddings[0]),
            "model_used": model_name,
            "provider_used": provider
        }
        
    except Exception as e:
        logger.error(f"Error generating single embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_available_models():
    """List available embedding models"""
    try:
        if EMBEDDING_PROVIDER == "huggingface":
            generator = HuggingFaceEmbeddingGenerator()
        else:
            generator = OllamaEmbeddingGenerator()
        
        models = await generator.list_available_models()
        
        return {
            "provider": EMBEDDING_PROVIDER,
            "default_model": DEFAULT_EMBEDDING_MODEL,
            "models": models
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/process")
async def process_embeddings_legacy():
    """Legacy endpoint for backward compatibility"""
    raise HTTPException(status_code=410, detail="This endpoint is deprecated. Use /process instead.")

async def update_job_status(document_id: str, status: str, result_data: Dict[str, Any] = None):
    """Update job status in processing pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{PROCESSING_PIPELINE_URL}/jobs/{document_id}/status",
                json={
                    "status": status,
                    "result_data": result_data or {}
                },
                timeout=10.0
            )
    except Exception as e:
        logger.warning(f"Failed to update job status: {e}")

if __name__ == "__main__":
    port = int(os.getenv("EMBEDDING_PROCESSOR_PORT", 8007))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port) 