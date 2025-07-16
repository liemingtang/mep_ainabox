from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MDIS Embedding Processor", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://processing-pipeline:8003")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "embedding-processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Embedding Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL,
        "qdrant_host": QDRANT_HOST
    }

@app.post("/api/v1/process")
async def process_embeddings():
    """Process document embeddings"""
    try:
        # Basic embedding processing - in a real implementation, this would generate
        # embeddings and store them in Qdrant
        return {
            "status": "processed",
            "embeddings": {
                "count": 1,
                "dimensions": 1536,
                "model": "text-embedding-ada-002"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing embeddings: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007) 