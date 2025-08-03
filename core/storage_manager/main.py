from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MDIS Storage Manager", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
NEO4J_HOST = os.getenv("NEO4J_HOST", "neo4j")
MINIO_HOST = os.getenv("MINIO_HOST", "minio")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "storage-manager"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Storage Manager",
        "version": "1.0.0",
        "storage_services": {
            "postgres": POSTGRES_HOST,
            "elasticsearch": ELASTICSEARCH_HOST,
            "qdrant": QDRANT_HOST,
            "neo4j": NEO4J_HOST,
            "minio": MINIO_HOST,
            "redis": REDIS_HOST
        }
    }

@app.get("/api/v1/storage/status")
async def get_storage_status():
    """Get the status of all storage services"""
    try:
        # In a real implementation, this would check the health of each storage service
        return {
            "postgres": "healthy",
            "elasticsearch": "healthy",
            "qdrant": "healthy",
            "neo4j": "healthy",
            "minio": "healthy",
            "redis": "healthy"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking storage status: {str(e)}")

@app.post("/api/v1/storage/store")
async def store_data():
    """Store data in appropriate storage services"""
    try:
        # In a real implementation, this would store data in the appropriate services
        return {
            "status": "stored",
            "locations": {
                "metadata": "postgres",
                "content": "elasticsearch",
                "embeddings": "qdrant",
                "relationships": "neo4j",
                "files": "minio",
                "cache": "redis"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("STORAGE_MANAGER_PORT", 8004))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port) 