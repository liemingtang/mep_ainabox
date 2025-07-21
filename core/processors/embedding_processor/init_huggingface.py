#!/usr/bin/env python3
"""
Initialize HuggingFace embedding models
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HuggingFace configuration
HF_DEFAULT_MODEL = os.getenv("HF_DEFAULT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_CACHE_DIR = os.getenv("HF_CACHE_DIR", "/app/cache/huggingface")
HF_DEVICE = os.getenv("HF_DEVICE", "cpu")
HF_BATCH_SIZE = int(os.getenv("HF_BATCH_SIZE", "32"))

# Recommended HuggingFace models
RECOMMENDED_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",      # 384 dimensions, fast
    "sentence-transformers/paraphrase-MiniLM-L3-v2", # 384 dimensions, very fast
    "sentence-transformers/all-mpnet-base-v2",     # 768 dimensions, high quality
    "sentence-transformers/e5-small-v2",           # 384 dimensions, good quality
    "sentence-transformers/e5-base-v2",            # 768 dimensions, excellent quality
    "sentence-transformers/e5-large-v2",           # 1024 dimensions, best quality
    "sentence-transformers/multi-qa-MiniLM-L6-cos-v1", # 384 dimensions, QA optimized
    "sentence-transformers/all-distilroberta-v1"   # 768 dimensions, balanced
]

async def check_huggingface_installation():
    """Check if HuggingFace dependencies are available"""
    try:
        import sentence_transformers
        import torch
        import transformers
        logger.info("✅ HuggingFace dependencies are available")
        logger.info(f"   - sentence-transformers: {sentence_transformers.__version__}")
        logger.info(f"   - torch: {torch.__version__}")
        logger.info(f"   - transformers: {transformers.__version__}")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing HuggingFace dependencies: {e}")
        return False

async def test_model_loading(model_name: str, cache_dir: str) -> bool:
    """Test loading a specific HuggingFace model"""
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info(f"🔄 Testing model: {model_name}")
        
        # Create cache directory if it doesn't exist
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Load model
        model = SentenceTransformer(
            model_name,
            cache_folder=cache_dir,
            device=HF_DEVICE
        )
        
        # Test embedding generation
        test_texts = ["Hello world", "This is a test sentence", "Another example"]
        embeddings = model.encode(
            test_texts,
            batch_size=HF_BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        
        dimensions = embeddings.shape[1] if len(embeddings.shape) > 1 else len(embeddings)
        logger.info(f"✅ Model {model_name} loaded successfully")
        logger.info(f"   - Dimensions: {dimensions}")
        logger.info(f"   - Device: {HF_DEVICE}")
        logger.info(f"   - Cache: {cache_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load model {model_name}: {e}")
        return False

async def download_model(model_name: str, cache_dir: str) -> bool:
    """Download a HuggingFace model"""
    try:
        logger.info(f"📥 Downloading model: {model_name}")
        
        # This will trigger the download
        success = await test_model_loading(model_name, cache_dir)
        
        if success:
            logger.info(f"✅ Successfully downloaded model: {model_name}")
        else:
            logger.error(f"❌ Failed to download model: {model_name}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error downloading model {model_name}: {e}")
        return False

async def list_available_models():
    """List currently available models"""
    try:
        from sentence_transformers import SentenceTransformer
        
        # Check which models are already cached
        cache_path = Path(HF_CACHE_DIR)
        if cache_path.exists():
            logger.info(f"📁 Cache directory: {HF_CACHE_DIR}")
            # This is a simplified check - in practice, you'd need to check the actual model files
            logger.info("   - Models will be downloaded on first use")
        else:
            logger.info(f"📁 Cache directory will be created: {HF_CACHE_DIR}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking available models: {e}")
        return False

async def main():
    """Main initialization function"""
    logger.info("🚀 Initializing HuggingFace for embedding processor...")
    
    # Check dependencies
    if not await check_huggingface_installation():
        logger.error("❌ HuggingFace dependencies are not available. Please install required packages.")
        sys.exit(1)
    
    # Create cache directory
    Path(HF_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Cache directory: {HF_CACHE_DIR}")
    
    # Test default model
    logger.info(f"🧪 Testing default model: {HF_DEFAULT_MODEL}")
    if not await test_model_loading(HF_DEFAULT_MODEL, HF_CACHE_DIR):
        logger.info(f"📥 Default model not found, downloading...")
        if not await download_model(HF_DEFAULT_MODEL, HF_CACHE_DIR):
            logger.error(f"❌ Failed to download default model '{HF_DEFAULT_MODEL}'")
            sys.exit(1)
    else:
        logger.info(f"✅ Default model '{HF_DEFAULT_MODEL}' is already available")
    
    # List available models
    await list_available_models()
    
    # Show recommended models
    logger.info("📋 Recommended HuggingFace models:")
    for i, model in enumerate(RECOMMENDED_MODELS, 1):
        logger.info(f"   {i}. {model}")
    
    logger.info("🎉 HuggingFace initialization completed successfully!")
    logger.info(f"📊 Default embedding model: {HF_DEFAULT_MODEL}")
    logger.info(f"💾 Cache directory: {HF_CACHE_DIR}")
    logger.info(f"🔧 Device: {HF_DEVICE}")
    logger.info(f"📦 Batch size: {HF_BATCH_SIZE}")
    logger.info("🔗 You can now use the embedding processor with HuggingFace!")
    
    # Usage instructions
    logger.info("\n📖 Usage Instructions:")
    logger.info("1. Set EMBEDDING_PROVIDER=huggingface in your environment")
    logger.info("2. Start the embedding processor service")
    logger.info("3. Models will be automatically downloaded on first use")
    logger.info("4. Use the /models endpoint to see available models")

if __name__ == "__main__":
    asyncio.run(main()) 