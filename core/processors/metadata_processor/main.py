from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MDIS Metadata Processor", version="1.0.0")

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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "metadata-processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Metadata Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL
    }

@app.post("/api/v1/process")
async def process_metadata():
    """Process document metadata"""
    try:
        # Basic metadata processing - in a real implementation, this would extract
        # metadata from documents
        return {
            "status": "processed",
            "metadata": {
                "title": "Sample Document",
                "author": "Unknown",
                "date": "2024-01-01",
                "type": "document",
                "pages": 1
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing metadata: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006) 