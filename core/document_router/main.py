from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="MDIS Document Router", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://processing-pipeline:8003")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "document-router"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Document Router",
        "version": "1.0.0",
        "services": {
            "core-processor": CORE_PROCESSOR_URL,
            "processing-pipeline": PROCESSING_PIPELINE_URL
        }
    }

@app.post("/api/v1/route")
async def route_document():
    """Route a document to appropriate processors"""
    try:
        # Basic routing logic - in a real implementation, this would analyze the document
        # and determine which processors to use
        return {
            "status": "routed",
            "processors": ["text-processor", "metadata-processor", "embedding-processor"],
            "priority": "normal"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error routing document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 