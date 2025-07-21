#!/usr/bin/env python3
"""
Configuration for Embedding Processor
"""

import os
from typing import Dict, Any

# Embedding Provider Configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama")  # "ollama" or "huggingface"

# Ollama Configuration
OLLAMA_CONFIG = {
    "host": os.getenv("OLLAMA_HOST", "ollama"),
    "port": os.getenv("OLLAMA_PORT", "11434"),
    "default_model": os.getenv("OLLAMA_DEFAULT_MODEL", "nomic-embed-text"),
    "base_url": f"http://{os.getenv('OLLAMA_HOST', 'ollama')}:{os.getenv('OLLAMA_PORT', '11434')}",
    "model_dimensions": {
        "nomic-embed-text": 768,
        "all-minilm": 384,
        "all-mpnet-base-v2": 768,
        "text-embedding-ada-002": 1536,
        "e5-large-v2": 1024,
        "e5-base-v2": 768,
        "e5-small-v2": 384
    }
}

# HuggingFace Configuration
HUGGINGFACE_CONFIG = {
    "default_model": os.getenv("HF_DEFAULT_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
    "cache_dir": os.getenv("HF_CACHE_DIR", "/app/cache/huggingface"),
    "device": os.getenv("HF_DEVICE", "cpu"),
    "batch_size": int(os.getenv("HF_BATCH_SIZE", "32")),
    "model_dimensions": {
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "sentence-transformers/paraphrase-MiniLM-L3-v2": 384,
        "sentence-transformers/e5-small-v2": 384,
        "sentence-transformers/e5-base-v2": 768,
        "sentence-transformers/e5-large-v2": 1024,
        "sentence-transformers/multi-qa-MiniLM-L6-cos-v1": 384,
        "sentence-transformers/all-distilroberta-v1": 768
    }
}

# Get default model based on provider
def get_default_model() -> str:
    """Get the default model for the current provider"""
    if EMBEDDING_PROVIDER == "huggingface":
        return HUGGINGFACE_CONFIG["default_model"]
    else:
        return OLLAMA_CONFIG["default_model"]

# Get model dimensions for a given model
def get_model_dimensions(model_name: str) -> int:
    """Get the expected dimensions for a model"""
    if EMBEDDING_PROVIDER == "huggingface":
        return HUGGINGFACE_CONFIG["model_dimensions"].get(model_name, 384)
    else:
        return OLLAMA_CONFIG["model_dimensions"].get(model_name, 768)

# Provider comparison
PROVIDER_COMPARISON = {
    "ollama": {
        "description": "Self-hosted Ollama models",
        "pros": [
            "Complete privacy and control",
            "No internet dependency",
            "Custom model support",
            "GPU acceleration support"
        ],
        "cons": [
            "Requires more resources",
            "Model management overhead",
            "Limited model selection"
        ],
        "best_for": [
            "High privacy requirements",
            "Offline environments",
            "Custom model needs"
        ]
    },
    "huggingface": {
        "description": "HuggingFace Transformers models",
        "pros": [
            "Wide model selection",
            "Easy setup",
            "Good performance",
            "Active community"
        ],
        "cons": [
            "Requires internet for initial download",
            "Limited offline capability",
            "Model size considerations"
        ],
        "best_for": [
            "Quick setup",
            "Wide model variety",
            "Development and testing"
        ]
    }
}

# Recommended models by use case
RECOMMENDED_MODELS = {
    "fast": {
        "ollama": "all-minilm",
        "huggingface": "sentence-transformers/paraphrase-MiniLM-L3-v2",
        "description": "Quick embeddings for real-time applications"
    },
    "balanced": {
        "ollama": "nomic-embed-text",
        "huggingface": "sentence-transformers/all-MiniLM-L6-v2",
        "description": "Good balance of speed and quality"
    },
    "quality": {
        "ollama": "e5-large-v2",
        "huggingface": "sentence-transformers/all-mpnet-base-v2",
        "description": "High-quality embeddings for critical applications"
    },
    "multilingual": {
        "ollama": "nomic-embed-text",
        "huggingface": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "description": "Support for multiple languages"
    }
}

def get_recommended_model(use_case: str = "balanced") -> str:
    """Get recommended model for a specific use case"""
    if use_case in RECOMMENDED_MODELS:
        provider_config = RECOMMENDED_MODELS[use_case]
        if EMBEDDING_PROVIDER in provider_config:
            return provider_config[EMBEDDING_PROVIDER]
    return get_default_model()

def get_provider_info() -> Dict[str, Any]:
    """Get information about the current provider"""
    return {
        "current_provider": EMBEDDING_PROVIDER,
        "default_model": get_default_model(),
        "comparison": PROVIDER_COMPARISON,
        "recommended_models": RECOMMENDED_MODELS
    } 