#!/usr/bin/env python3
"""
MDIS Dashboard Service

A comprehensive web dashboard for monitoring:
- File processing status (from scan folder and file watcher)
- System health of all processing services
- Data analytics and statistics
- Real-time processing pipeline status
"""

import os
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://localhost:8001")
FILE_WATCHER_URL = os.getenv("FILE_WATCHER_URL", "http://localhost:8009")
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://localhost:8004")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
NEO4J_URL = os.getenv("NEO4J_URL", "http://localhost:7474")

# Authentication credentials
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "qdrant_api_key")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")

# Service endpoints for health checks
SERVICES = {
    "core-processor": f"{CORE_PROCESSOR_URL}/health",
    "file-watcher": f"{FILE_WATCHER_URL}/health",
    "storage-manager": f"{STORAGE_MANAGER_URL}/health",
    "text-processor": "http://localhost:8005/health",
    "metadata-processor": "http://localhost:8006/health",
    "embedding-processor": "http://localhost:8007/health",
    "entity-processor": "http://localhost:8008/health",
    "processing-pipeline": "http://localhost:8003/health",
    "document-router": "http://localhost:8002/health",
    "api-gateway": "http://localhost:8000/health",
    "elasticsearch": f"{ELASTICSEARCH_URL}/_cluster/health",
    "qdrant": f"{QDRANT_URL}/collections",
    "neo4j": f"{NEO4J_URL}/db/data/",
}

app = FastAPI(title="MDIS Dashboard", version="1.0.0")

# Create templates directory
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class ServiceHealth(BaseModel):
    service: str
    status: str
    response_time: float
    last_check: datetime
    details: Optional[Dict] = None

class DocumentStatus(BaseModel):
    id: str
    filename: str
    source: str
    processing_status: str
    created_at: datetime
    updated_at: datetime
    file_size: int
    document_type: str

class DashboardStats(BaseModel):
    total_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    pending_documents: int
    healthy_services: int
    total_services: int
    elasticsearch_docs: int
    qdrant_collections: int

async def check_service_health(service_name: str, url: str) -> ServiceHealth:
    """Check health of a single service"""
    start_time = datetime.now()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Add authentication headers for specific services
            headers = {}
            if service_name == "qdrant":
                headers["api-key"] = QDRANT_API_KEY
            elif service_name == "neo4j":
                # For Neo4j, we'll use a simple endpoint that doesn't require auth
                url = f"{NEO4J_URL}/browser/"
            
            response = await client.get(url, headers=headers)
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                details = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                return ServiceHealth(
                    service=service_name,
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.now(),
                    details=details
                )
            else:
                return ServiceHealth(
                    service=service_name,
                    status="unhealthy",
                    response_time=response_time,
                    last_check=datetime.now(),
                    details={"status_code": response.status_code}
                )
    except Exception as e:
        response_time = (datetime.now() - start_time).total_seconds()
        return ServiceHealth(
            service=service_name,
            status="error",
            response_time=response_time,
            last_check=datetime.now(),
            details={"error": str(e)}
        )

async def get_all_service_health() -> List[ServiceHealth]:
    """Check health of all services"""
    tasks = [check_service_health(name, url) for name, url in SERVICES.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    health_results = []
    for result in results:
        if isinstance(result, ServiceHealth):
            health_results.append(result)
        else:
            # Handle exceptions
            health_results.append(ServiceHealth(
                service="unknown",
                status="error",
                response_time=0.0,
                last_check=datetime.now(),
                details={"error": str(result)}
            ))
    
    return health_results

async def get_documents() -> List[DocumentStatus]:
    """Get all documents from core processor"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CORE_PROCESSOR_URL}/documents")
            if response.status_code == 200:
                documents = response.json()
                return [DocumentStatus(**doc) for doc in documents]
            else:
                logger.error(f"Failed to get documents: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return []

async def get_elasticsearch_stats() -> Dict:
    """Get Elasticsearch statistics"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get indices
            indices_response = await client.get(f"{ELASTICSEARCH_URL}/_cat/indices?format=json")
            if indices_response.status_code == 200:
                indices = indices_response.json()
                total_docs = sum(int(idx.get('docs.count', 0)) for idx in indices)
                return {
                    "total_documents": total_docs,
                    "indices": indices
                }
            else:
                return {"total_documents": 0, "indices": []}
    except Exception as e:
        logger.error(f"Error getting Elasticsearch stats: {e}")
        return {"total_documents": 0, "indices": []}

async def get_qdrant_stats() -> Dict:
    """Get Qdrant statistics"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"api-key": QDRANT_API_KEY}
            response = await client.get(f"{QDRANT_URL}/collections", headers=headers)
            if response.status_code == 200:
                collections = response.json()
                collections_list = collections.get("result", {}).get("collections", [])
                return {
                    "collections": collections_list,
                    "total_collections": len(collections_list)
                }
            else:
                return {"collections": [], "total_collections": 0}
    except Exception as e:
        logger.error(f"Error getting Qdrant stats: {e}")
        return {"collections": [], "total_collections": 0}

async def get_dashboard_stats() -> DashboardStats:
    """Get comprehensive dashboard statistics"""
    documents = await get_documents()
    service_health = await get_all_service_health()
    es_stats = await get_elasticsearch_stats()
    qdrant_stats = await get_qdrant_stats()
    
    # Count documents by status
    status_counts = {}
    for doc in documents:
        status = doc.processing_status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Count healthy services
    healthy_services = sum(1 for service in service_health if service.status == "healthy")
    
    return DashboardStats(
        total_documents=len(documents),
        processing_documents=status_counts.get("processing", 0),
        completed_documents=status_counts.get("completed", 0),
        failed_documents=status_counts.get("failed", 0),
        pending_documents=status_counts.get("pending", 0),
        healthy_services=healthy_services,
        total_services=len(service_health),
        elasticsearch_docs=es_stats.get("total_documents", 0),
        qdrant_collections=qdrant_stats.get("total_collections", 0)
    )

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/health")
async def get_health():
    """Get health status of all services"""
    health_results = await get_all_service_health()
    return {"services": health_results, "timestamp": datetime.now().isoformat()}

@app.get("/api/documents")
async def get_documents_api():
    """Get all documents"""
    documents = await get_documents()
    return {"documents": documents, "count": len(documents)}

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    stats = await get_dashboard_stats()
    return stats

@app.get("/api/documents/{document_id}")
async def get_document_detail(document_id: str):
    """Get detailed information about a specific document"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get basic document info
            doc_response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{document_id}")
            if doc_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Document not found")
            
            document = doc_response.json()
            
            # Get processing status
            status_response = await client.get(f"{CORE_PROCESSOR_URL}/documents/{document_id}/processing-status")
            processing_status = status_response.json() if status_response.status_code == 200 else None
            
            # Get from Elasticsearch
            es_response = await client.get(f"{ELASTICSEARCH_URL}/documents/_search?q=document_id:{document_id}")
            es_data = es_response.json() if es_response.status_code == 200 else None
            
            return {
                "document": document,
                "processing_status": processing_status,
                "elasticsearch_data": es_data
            }
    except Exception as e:
        logger.error(f"Error getting document detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/services")
async def get_services():
    """Get detailed service information"""
    health_results = await get_all_service_health()
    return {"services": health_results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010) 