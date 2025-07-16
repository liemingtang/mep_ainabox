from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="MDIS Processing Pipeline", version="1.0.0")

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
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://storage-manager:8004")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "processing-pipeline"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Processing Pipeline",
        "version": "1.0.0",
        "services": {
            "core-processor": CORE_PROCESSOR_URL,
            "storage-manager": STORAGE_MANAGER_URL
        }
    }

@app.post("/api/v1/process")
async def process_document():
    """Process a document through the pipeline"""
    try:
        # Basic processing logic - in a real implementation, this would orchestrate
        # the document through various processors
        return {
            "status": "processing",
            "job_id": "job_123",
            "steps": ["text-extraction", "metadata-extraction", "embedding-generation"],
            "estimated_time": "30 seconds"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/api/v1/status/{job_id}")
async def get_processing_status(job_id: str):
    """Get the status of a processing job"""
    try:
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "results": {
                "text_extracted": True,
                "metadata_extracted": True,
                "embeddings_generated": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 