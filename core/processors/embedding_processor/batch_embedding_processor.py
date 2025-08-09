#!/usr/bin/env python3
"""
Batch Embedding Processor

Reads text content from a file, generates vector embeddings (via Ollama by default),
and stores them into Qdrant using environment variables for connection details.

Environment variables:
  - QDRANT_HOST (default: qdrant)
  - QDRANT_PORT (default: 6333)
  - QDRANT_API_KEY (optional)
  - QDRANT_COLLECTION (default: documents)
  - EMBEDDING_PROVIDER (default: ollama)  # Only 'ollama' supported in this batch script
  - OLLAMA_HOST (default: ollama)
  - OLLAMA_PORT (default: 11434)
  - OLLAMA_DEFAULT_MODEL (default: nomic-embed-text)
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


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
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
    ollama_host = os.getenv("OLLAMA_HOST", "ollama")
    ollama_port = os.getenv("OLLAMA_PORT", "11434")
    ollama_model = os.getenv("OLLAMA_DEFAULT_MODEL", "nomic-embed-text")
    ollama_base = f"http://{ollama_host}:{ollama_port}"

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

    # Generate embeddings
    if provider != "ollama":
        logger.error("Only EMBEDDING_PROVIDER=ollama is supported in batch script. Set env accordingly.")
        return 2
    embeddings = await generate_ollama_embeddings(chunks, ollama_base, ollama_model)
    dims = len(embeddings[0]) if embeddings else 0
    logger.info(f"Generated {len(embeddings)} embeddings of dimension {dims}")

    # Ensure collection and store
    await ensure_qdrant_collection(q_host, q_port, q_api, q_collection, dims or 768)
    await store_embeddings_qdrant(q_host, q_port, q_api, q_collection, args.document_id, chunks, embeddings, ollama_model, provider)

    # Emit a concise JSON summary to stdout
    print(json.dumps({
        "success": True,
        "embeddings_count": len(embeddings),
        "vector_dimensions": dims,
        "collection": q_collection,
        "provider_used": provider,
        "model_used": ollama_model
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


