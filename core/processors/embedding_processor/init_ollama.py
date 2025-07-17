#!/usr/bin/env python3
"""
Initialize Ollama with default embedding models
"""

import asyncio
import httpx
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Recommended embedding models
RECOMMENDED_MODELS = [
    "nomic-embed-text",      # 768 dimensions, high quality
    "all-minilm",           # 384 dimensions, fast
    "all-mpnet-base-v2",    # 768 dimensions, high quality
    "e5-large-v2",          # 1024 dimensions, excellent quality
    "e5-base-v2",           # 768 dimensions, good quality
    "e5-small-v2"           # 384 dimensions, fast
]

async def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
            response.raise_for_status()
            logger.info("✅ Ollama is running and accessible")
            return True
    except Exception as e:
        logger.error(f"❌ Cannot connect to Ollama: {e}")
        return False

async def list_available_models():
    """List currently available models in Ollama"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            logger.info(f"📋 Available models: {available_models}")
            return available_models
            
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

async def pull_model(model_name: str):
    """Pull a model to Ollama"""
    try:
        logger.info(f"📥 Pulling model: {model_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json={"name": model_name},
                timeout=300.0  # 5 minutes timeout for model pulling
            )
            response.raise_for_status()
            logger.info(f"✅ Successfully pulled model: {model_name}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to pull model {model_name}: {e}")
        return False

async def test_embedding_generation(model_name: str):
    """Test embedding generation with a model"""
    try:
        test_text = "This is a test sentence for embedding generation."
        logger.info(f"🧪 Testing embedding generation with model: {model_name}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": model_name,
                    "prompt": test_text
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            if embedding:
                logger.info(f"✅ Embedding generation successful! Dimensions: {len(embedding)}")
                return True
            else:
                logger.error(f"❌ No embedding returned for model: {model_name}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error testing embedding generation: {e}")
        return False

async def main():
    """Main initialization function"""
    logger.info("🚀 Initializing Ollama for embedding processor...")
    
    # Check Ollama connection
    if not await check_ollama_connection():
        logger.error("❌ Ollama is not accessible. Please ensure Ollama is running.")
        sys.exit(1)
    
    # List current models
    available_models = await list_available_models()
    
    # Check if default model is available
    if DEFAULT_EMBEDDING_MODEL not in available_models:
        logger.info(f"📥 Default model '{DEFAULT_EMBEDDING_MODEL}' not found, pulling...")
        if not await pull_model(DEFAULT_EMBEDDING_MODEL):
            logger.error(f"❌ Failed to pull default model '{DEFAULT_EMBEDDING_MODEL}'")
            sys.exit(1)
    else:
        logger.info(f"✅ Default model '{DEFAULT_EMBEDDING_MODEL}' is already available")
    
    # Test embedding generation
    if not await test_embedding_generation(DEFAULT_EMBEDDING_MODEL):
        logger.error(f"❌ Failed to test embedding generation with '{DEFAULT_EMBEDDING_MODEL}'")
        sys.exit(1)
    
    # Optionally pull other recommended models
    logger.info("📋 Checking other recommended models...")
    for model in RECOMMENDED_MODELS:
        if model != DEFAULT_EMBEDDING_MODEL and model not in available_models:
            logger.info(f"📥 Pulling recommended model: {model}")
            await pull_model(model)
    
    logger.info("🎉 Ollama initialization completed successfully!")
    logger.info(f"📊 Default embedding model: {DEFAULT_EMBEDDING_MODEL}")
    logger.info(f"🌐 Ollama URL: {OLLAMA_BASE_URL}")
    logger.info("🔗 You can now use the embedding processor with Ollama!")

if __name__ == "__main__":
    asyncio.run(main()) 