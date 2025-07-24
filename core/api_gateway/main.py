from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(title="MDIS API Gateway", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://localhost:8001")
DOCUMENT_ROUTER_URL = os.getenv("DOCUMENT_ROUTER_URL", "http://localhost:8002")
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://localhost:8004")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS API Gateway",
        "version": "1.0.0",
        "services": {
            "core-processor": CORE_SERVICE_URL,
            "document-router": DOCUMENT_ROUTER_URL,
            "processing-pipeline": PROCESSING_PIPELINE_URL,
            "storage-manager": STORAGE_MANAGER_URL
        }
    }

@app.get("/api/v1/documents")
async def list_documents():
    """List all documents"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CORE_SERVICE_URL}/api/v1/documents")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to core service: {str(e)}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {"message": "API Gateway metrics", "status": "available"}

@app.post("/api/v1/documents/upload")
async def upload_document():
    """Upload a document"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{CORE_SERVICE_URL}/api/v1/documents/upload")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to core service: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 