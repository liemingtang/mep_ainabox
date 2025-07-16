from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MDIS Entity Processor", version="1.0.0")

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
NEO4J_HOST = os.getenv("NEO4J_HOST", "neo4j")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "entity-processor"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Entity Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL,
        "neo4j_host": NEO4J_HOST
    }

@app.post("/api/v1/process")
async def process_entities():
    """Process document entities"""
    try:
        # Basic entity processing - in a real implementation, this would extract
        # entities and store relationships in Neo4j
        return {
            "status": "processed",
            "entities": {
                "count": 5,
                "types": ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing entities: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008) 