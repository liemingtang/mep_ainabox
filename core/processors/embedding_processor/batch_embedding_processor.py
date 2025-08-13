#!/usr/bin/env python3
"""
Batch Embedding Processor

Reads text content from a file, generates vector embeddings (via Ollama or HuggingFace),
and stores them into Qdrant using environment variables for connection details.

Environment variables:
  - QDRANT_HOST (default: qdrant)
  - QDRANT_PORT (default: 6333)
  - QDRANT_API_KEY (optional)
  - QDRANT_COLLECTION (default: documents)
  - EMBEDDING_PROVIDER (default: ollama)  # 'ollama' or 'huggingface'
  - OLLAMA_HOST (default: ollama)
  - OLLAMA_PORT (default: 11434)
  - OLLAMA_DEFAULT_MODEL (default: nomic-embed-text)
  - HUGGINGFACE_HOST (default: localhost)
  - HUGGINGFACE_PORT (default: 8082)
  - HUGGINGFACE_MODEL (default: sentence-transformers/all-MiniLM-L6-v2)
  - EMBEDDING_CHUNK_SIZE (default: 300)  # Character limit per chunk
  - EMBEDDING_CHUNK_OVERLAP (default: 50)  # Character overlap between chunks
  - EMBEDDING_BATCH_SIZE (default: 150)  # Maximum chunks per batch for HuggingFace
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import httpx


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    # Get chunk size and overlap from environment variables with defaults
    if chunk_size is None:
        chunk_size = int(os.getenv("EMBEDDING_CHUNK_SIZE", "200"))
    if chunk_overlap is None:
        chunk_overlap = int(os.getenv("EMBEDDING_CHUNK_OVERLAP", "20"))
    if len(text) <= chunk_size:
        return [text]
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        # Try to break at a sentence boundary
        if end < length:
            sentence_endings = ['. ', '! ', '? ', '\n\n']
            best_break = end
            for ending in sentence_endings:
                pos = text.rfind(ending, start, end)
                if pos > start and pos < end:
                    best_break = pos + len(ending.strip())
                    break
            chunk = text[start:best_break].strip()
        else:
            chunk = text[start:].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return chunks


async def generate_ollama_embeddings(texts: List[str], base_url: str, model_name: str) -> List[List[float]]:
    embeddings: List[List[float]] = []
    async with httpx.AsyncClient() as client:
        for text in texts:
            resp = await client.post(
                f"{base_url}/api/embeddings",
                json={"model": model_name, "prompt": text},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding", [])
            if not embedding:
                raise RuntimeError("No embedding returned from Ollama")
            embeddings.append(embedding)
    return embeddings


async def generate_huggingface_embeddings(texts: List[str], base_url: str, model_name: str) -> List[List[float]]:
    embeddings: List[List[float]] = []
    async with httpx.AsyncClient() as client:
        # Process chunks in batches to avoid exceeding the batch size limit
        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "150"))  # Default to 150 to be safe
        logger.info(f"Processing {len(texts)} chunks in batches of {batch_size}")
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch_texts)} chunks)")
            
            # HuggingFace Text Embeddings Inference service expects a list of texts
            # The service is configured to use sentence-transformers/all-MiniLM-L6-v2
            payload = {
                "inputs": batch_texts
            }
            resp = await client.post(
                f"{base_url}/embed",
                json=payload,
                timeout=120.0,  # Longer timeout for HuggingFace
            )
            resp.raise_for_status()
            data = resp.json()
            
            # The new HuggingFace Text Embeddings Inference service returns embeddings directly
            batch_embeddings = []
            if isinstance(data, list):
                # Direct list of embeddings
                batch_embeddings = data
            elif isinstance(data, dict) and "embeddings" in data:
                # Response with embeddings key
                batch_embeddings = data["embeddings"]
            else:
                # Try to extract embeddings from the response
                batch_embeddings = data.get("embeddings", [])
                
            if not batch_embeddings:
                raise RuntimeError(f"No embeddings returned from HuggingFace service for batch {i//batch_size + 1}")
                
            # Ensure all embeddings are lists of floats
            for j, emb in enumerate(batch_embeddings):
                if not isinstance(emb, list):
                    raise RuntimeError(f"Invalid embedding format at batch {i//batch_size + 1}, index {j}")
                if not all(isinstance(x, (int, float)) for x in emb):
                    raise RuntimeError(f"Invalid embedding values at batch {i//batch_size + 1}, index {j}")
            
            embeddings.extend(batch_embeddings)
            logger.info(f"Successfully processed batch {i//batch_size + 1} ({len(batch_embeddings)} embeddings)")
                
    return embeddings


async def ensure_qdrant_collection(host: str, port: int, api_key: str, collection: str, dimensions: int) -> None:
    headers = {"api-key": api_key} if api_key else {}
    base_url = f"http://{host}:{port}"
    async with httpx.AsyncClient() as client:
        # Check
        r = await client.get(f"{base_url}/collections/{collection}", headers=headers, timeout=10.0)
        if r.status_code == 200:
            return
        # Create
        payload = {
            "vectors": {
                "size": dimensions,
                "distance": "Cosine"
            }
        }
        rc = await client.put(
            f"{base_url}/collections/{collection}",
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30.0,
        )
        rc.raise_for_status()


async def store_embeddings_qdrant(host: str, port: int, api_key: str, collection: str,
                                  document_id: str, texts: List[str], embeddings: List[List[float]],
                                  model_used: str, provider_used: str) -> None:
    headers = {"api-key": api_key, "Content-Type": "application/json"} if api_key else {"Content-Type": "application/json"}
    base_url = f"http://{host}:{port}"
    points: List[Dict[str, Any]] = []
    for i, (emb, txt) in enumerate(zip(embeddings, texts)):
        pid = int.from_bytes(f"{document_id}_{i}".encode("utf-8"), byteorder="big", signed=False) % (2**63)
        points.append({
            "id": pid,
            "vector": emb,
            "payload": {
                "document_id": document_id,
                "chunk_index": i,
                "text": txt[:1000],
                "text_length": len(txt),
                "model_used": model_used,
                "provider_used": provider_used,
                "created_at": datetime.utcnow().isoformat(),
            }
        })
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{base_url}/collections/{collection}/points",
            headers=headers,
            json={"points": points},
            timeout=30.0,
        )
        resp.raise_for_status()


async def main_async(args: argparse.Namespace) -> int:
    # Load envs
    q_host = os.getenv("QDRANT_HOST", "qdrant")
    q_port = int(os.getenv("QDRANT_PORT", "6333"))
    q_api = os.getenv("QDRANT_API_KEY", "")
    q_collection = os.getenv("QDRANT_COLLECTION", "documents")

    provider = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
    
    # Ollama configuration
    ollama_host = os.getenv("OLLAMA_HOST", "ollama")
    ollama_port = os.getenv("OLLAMA_PORT", "11434")
    ollama_model = os.getenv("OLLAMA_DEFAULT_MODEL", "nomic-embed-text")
    ollama_base = f"http://{ollama_host}:{ollama_port}"
    
    # HuggingFace configuration (Text Embeddings Inference service)
    hf_host = os.getenv("HUGGINGFACE_HOST", "localhost")
    hf_port = os.getenv("HUGGINGFACE_PORT", "8082")
    hf_model = os.getenv("HUGGINGFACE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    hf_base = f"http://{hf_host}:{hf_port}"

    # Read text
    text_path = Path(args.text_file)
    if not text_path.exists() or not text_path.is_file():
        logger.error(f"Text file not found: {text_path}")
        return 1
    text_content = text_path.read_text(encoding="utf-8", errors="ignore")
    if not text_content.strip():
        logger.warning("Empty text content; nothing to embed")
        return 0

    # Chunk
    chunks = chunk_text(text_content)
    logger.info(f"Chunked text into {len(chunks)} chunks")

    # Generate embeddings based on provider
    if provider == "ollama":
        embeddings = await generate_ollama_embeddings(chunks, ollama_base, ollama_model)
        model_used = ollama_model
    elif provider == "huggingface":
        embeddings = await generate_huggingface_embeddings(chunks, hf_base, hf_model)
        model_used = hf_model
    else:
        logger.error(f"Unsupported EMBEDDING_PROVIDER: {provider}. Use 'ollama' or 'huggingface'")
        return 2
        
    dims = len(embeddings[0]) if embeddings else 0
    logger.info(f"Generated {len(embeddings)} embeddings of dimension {dims} using {provider}")

    # Ensure collection and store
    # Use appropriate default dimensions based on provider
    default_dims = 384 if provider == "huggingface" else 768
    await ensure_qdrant_collection(q_host, q_port, q_api, q_collection, dims or default_dims)
    await store_embeddings_qdrant(q_host, q_port, q_api, q_collection, args.document_id, chunks, embeddings, model_used, provider)

    # Emit a concise JSON summary to stdout
    print(json.dumps({
        "success": True,
        "embeddings_count": len(embeddings),
        "vector_dimensions": dims,
        "collection": q_collection,
        "provider_used": provider,
        "model_used": model_used
    }))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch embedding processor for MEP AI NABOX")
    parser.add_argument("--text-file", required=True, help="Path to a UTF-8 text file containing content to embed")
    parser.add_argument("--document-id", required=True, help="Document identifier to associate embeddings with")
    args = parser.parse_args()

    try:
        import asyncio
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Embedding processor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


