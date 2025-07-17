#!/usr/bin/env python3
"""
Example integration script for n8n workflows with the embedding processor
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any

# Configuration
EMBEDDING_SERVICE_URL = "http://localhost:8007"
DEFAULT_MODEL = "nomic-embed-text"

class EmbeddingServiceClient:
    """Client for interacting with the embedding processor service"""
    
    def __init__(self, base_url: str = EMBEDDING_SERVICE_URL):
        self.base_url = base_url
    
    async def get_embedding(self, text: str, model: str = DEFAULT_MODEL) -> List[float]:
        """Get embedding for a single text"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embed?text={text}&model={model}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["embedding"]
    
    async def search_similar(self, query: str, limit: int = 10, model: str = DEFAULT_MODEL) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={"text": query, "limit": limit, "model": model},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["results"]
    
    async def process_document(self, document_id: str, text: str, metadata: Dict[str, Any] = None, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
        """Process a document and store embeddings"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/process",
                json={
                    "document_id": document_id,
                    "text_content": text,
                    "metadata": metadata or {},
                    "model": model
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/models", timeout=10.0)
            response.raise_for_status()
            return response.json()["ollama_models"]

# Example n8n workflow functions
async def n8n_workflow_example_1():
    """Example 1: Simple text embedding for n8n"""
    client = EmbeddingServiceClient()
    
    # This would be called from n8n HTTP Request node
    text = "This is a sample text for embedding generation"
    
    try:
        embedding = await client.get_embedding(text)
        
        # Return data that n8n can use
        return {
            "success": True,
            "text": text,
            "embedding": embedding,
            "dimensions": len(embedding),
            "model_used": DEFAULT_MODEL
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def n8n_workflow_example_2():
    """Example 2: Document similarity search for n8n"""
    client = EmbeddingServiceClient()
    
    # This would be called from n8n HTTP Request node
    query = "machine learning algorithms"
    
    try:
        results = await client.search_similar(query, limit=5)
        
        # Format results for n8n
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result.get("score", 0),
                "document_id": result.get("payload", {}).get("document_id", ""),
                "text": result.get("payload", {}).get("text", ""),
                "metadata": result.get("payload", {}).get("metadata", {})
            })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "total_found": len(formatted_results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def n8n_workflow_example_3():
    """Example 3: Batch document processing for n8n"""
    client = EmbeddingServiceClient()
    
    # This would be called from n8n HTTP Request node
    documents = [
        {
            "id": "doc1",
            "text": "First document about artificial intelligence",
            "metadata": {"source": "file1.txt", "category": "AI"}
        },
        {
            "id": "doc2", 
            "text": "Second document about machine learning",
            "metadata": {"source": "file2.txt", "category": "ML"}
        }
    ]
    
    try:
        results = []
        for doc in documents:
            result = await client.process_document(
                doc["id"],
                doc["text"],
                doc["metadata"]
            )
            results.append(result)
        
        return {
            "success": True,
            "processed_documents": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# n8n HTTP endpoint simulation
async def simulate_n8n_http_request(endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Simulate n8n HTTP request to the embedding service"""
    client = EmbeddingServiceClient()
    
    if endpoint == "embed":
        text = data.get("text", "default text")
        model = data.get("model", DEFAULT_MODEL)
        embedding = await client.get_embedding(text, model)
        return {
            "text": text,
            "embedding": embedding,
            "dimensions": len(embedding),
            "model_used": model
        }
    
    elif endpoint == "search":
        query = data.get("text", "default query")
        limit = data.get("limit", 10)
        model = data.get("model", DEFAULT_MODEL)
        results = await client.search_similar(query, limit, model)
        return {
            "query": query,
            "results": results,
            "total_found": len(results),
            "model_used": model
        }
    
    elif endpoint == "process":
        document_id = data.get("document_id", "default_id")
        text = data.get("text_content", "default content")
        metadata = data.get("metadata", {})
        model = data.get("model", DEFAULT_MODEL)
        result = await client.process_document(document_id, text, metadata, model)
        return result
    
    else:
        raise ValueError(f"Unknown endpoint: {endpoint}")

# Example usage and testing
async def main():
    """Main function to demonstrate the integration"""
    print("🚀 n8n Integration Examples")
    print("=" * 50)
    
    # Test 1: Simple embedding
    print("\n1. Simple Text Embedding:")
    result1 = await n8n_workflow_example_1()
    print(json.dumps(result1, indent=2))
    
    # Test 2: Similarity search
    print("\n2. Document Similarity Search:")
    result2 = await n8n_workflow_example_2()
    print(json.dumps(result2, indent=2))
    
    # Test 3: Batch processing
    print("\n3. Batch Document Processing:")
    result3 = await n8n_workflow_example_3()
    print(json.dumps(result3, indent=2))
    
    # Test 4: Direct HTTP simulation
    print("\n4. Direct HTTP Request Simulation:")
    try:
        http_result = await simulate_n8n_http_request("embed", {
            "text": "Hello from n8n!",
            "model": "nomic-embed-text"
        })
        print(json.dumps(http_result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n✅ Integration examples completed!")

if __name__ == "__main__":
    asyncio.run(main()) 