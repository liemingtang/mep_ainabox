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
import subprocess
import threading
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs - Use localhost with host-gateway mapping
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://localhost:8001")
FILE_WATCHER_URL = os.getenv("FILE_WATCHER_URL", "http://localhost:8009")
STORAGE_MANAGER_URL = os.getenv("STORAGE_MANAGER_URL", "http://localhost:8004")
HOST_VOLUME_MANAGER_URL = os.getenv("HOST_VOLUME_MANAGER_URL", "http://localhost:8011")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
NEO4J_URL = os.getenv("NEO4J_URL", "http://localhost:7474")

# Authentication credentials
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "qdrant_api_key")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")

# Configuration management
CONFIG_FILE = "config/dashboard_config.json"
os.makedirs("config", exist_ok=True)

# Default configuration items
DEFAULT_CONFIG = {
    "api_keys": [
        {"key": "OPENAI_API_KEY", "value": "", "description": "OpenAI API key for text processing", "category": "api_keys", "is_sensitive": True},
        {"key": "ANTHROPIC_API_KEY", "value": "", "description": "Anthropic API key for Claude models", "category": "api_keys", "is_sensitive": True},
        {"key": "HUGGINGFACE_API_TOKEN", "value": "", "description": "Hugging Face API token", "category": "api_keys", "is_sensitive": True},
        {"key": "QDRANT_API_KEY", "value": QDRANT_API_KEY, "description": "Qdrant vector database API key", "category": "api_keys", "is_sensitive": True},
    ],
    "service_endpoints": [
        {"key": "CORE_PROCESSOR_URL", "value": CORE_PROCESSOR_URL, "description": "Core processor service URL", "category": "service_endpoints"},
        {"key": "FILE_WATCHER_URL", "value": FILE_WATCHER_URL, "description": "File watcher service URL", "category": "service_endpoints"},
        {"key": "STORAGE_MANAGER_URL", "value": STORAGE_MANAGER_URL, "description": "Storage manager service URL", "category": "service_endpoints"},
        {"key": "ELASTICSEARCH_URL", "value": ELASTICSEARCH_URL, "description": "Elasticsearch service URL", "category": "service_endpoints"},
        {"key": "QDRANT_URL", "value": QDRANT_URL, "description": "Qdrant vector database URL", "category": "service_endpoints"},
        {"key": "NEO4J_URL", "value": NEO4J_URL, "description": "Neo4j graph database URL", "category": "service_endpoints"},
    ],
    "database_credentials": [
        {"key": "POSTGRES_HOST", "value": "localhost", "description": "PostgreSQL database host", "category": "database_credentials"},
        {"key": "POSTGRES_PORT", "value": "5432", "description": "PostgreSQL database port", "category": "database_credentials"},
        {"key": "POSTGRES_DB", "value": "mep_ainabox", "description": "PostgreSQL database name", "category": "database_credentials"},
        {"key": "POSTGRES_USER", "value": "mep_user", "description": "PostgreSQL database user", "category": "database_credentials"},
        {"key": "POSTGRES_PASSWORD", "value": "", "description": "PostgreSQL database password", "category": "database_credentials", "is_sensitive": True},
        {"key": "NEO4J_USER", "value": NEO4J_USER, "description": "Neo4j database user", "category": "database_credentials"},
        {"key": "NEO4J_PASSWORD", "value": NEO4J_PASSWORD, "description": "Neo4j database password", "category": "database_credentials", "is_sensitive": True},
    ],
    "system_settings": [
        {"key": "ADMIN_EMAIL", "value": "admin@example.com", "description": "Administrator email address", "category": "system_settings"},
        {"key": "SYSTEM_ENVIRONMENT", "value": "development", "description": "System environment (development/production)", "category": "system_settings"},
        {"key": "DEBUG", "value": "true", "description": "Enable debug mode", "category": "system_settings"},
        {"key": "LOG_LEVEL", "value": "INFO", "description": "Logging level", "category": "system_settings"},
        {"key": "MAX_FILE_SIZE", "value": "100MB", "description": "Maximum file size for processing", "category": "system_settings"},
        {"key": "SUPPORTED_FORMATS", "value": "pdf,docx,txt,html", "description": "Supported document formats", "category": "system_settings"},
    ],
    "processing_settings": [
        {"key": "EMBEDDING_MODEL", "value": "text-embedding-ada-002", "description": "Default embedding model", "category": "processing_settings"},
        {"key": "TEXT_MODEL", "value": "gpt-3.5-turbo", "description": "Default text processing model", "category": "processing_settings"},
        {"key": "BATCH_SIZE", "value": "10", "description": "Processing batch size", "category": "processing_settings"},
        {"key": "TIMEOUT_SECONDS", "value": "300", "description": "Processing timeout in seconds", "category": "processing_settings"},
    ]
}

# Service information with enhanced configuration and metrics endpoints
SERVICE_INFO = {
    "core-processor": {
        "name": "Core Processor",
        "description": "Main document processing orchestrator",
        "port": 8001,
        "url": CORE_PROCESSOR_URL,
        "endpoints": ["/health", "/documents", "/stats", "/metrics"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/core-processor.log", "/app/logs/app.log"],
        "docker_container": "mep-core-processor",
        "admin_ui": None
    },
    "file-watcher": {
        "name": "File Watcher",
        "description": "Monitors folders for new documents",
        "port": 8009,
        "url": FILE_WATCHER_URL,
        "endpoints": ["/health", "/api/v1/watch/status", "/api/v1/watch/processed"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/file-watcher.log", "/app/logs/app.log"],
        "docker_container": "mep-file-watcher",
        "admin_ui": None
    },
    "host-volume-manager": {
        "name": "Host Volume Manager",
        "description": "Dynamically mounts local folders to shared Docker volumes",
        "port": 8011,
        "url": HOST_VOLUME_MANAGER_URL,
        "endpoints": ["/health", "/mount", "/list", "/unmount"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/host-volume-manager.log", "/app/logs/app.log"],
        "docker_container": None,  # Runs on host, not in container
        "admin_ui": None
    },
    "storage-manager": {
        "name": "Storage Manager",
        "description": "Unified data storage and retrieval interface",
        "port": 8004,
        "url": STORAGE_MANAGER_URL,
        "endpoints": ["/health", "/storage/stats", "/storage/backup"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/storage-manager.log", "/app/logs/app.log"],
        "docker_container": "mep-storage-manager",
        "admin_ui": None
    },
    "text-processor": {
        "name": "Text Processor",
        "description": "Text extraction and cleaning service",
        "port": 8005,
        "url": "http://localhost:8005",
        "endpoints": ["/health", "/extract-text", "/process"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/text-processor.log", "/app/logs/app.log"],
        "docker_container": "mep-text-processor",
        "admin_ui": None
    },
    "metadata-processor": {
        "name": "Metadata Processor",
        "description": "Metadata extraction and validation service",
        "port": 8006,
        "url": "http://localhost:8006",
        "endpoints": ["/health", "/extract-metadata", "/validate"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/metadata-processor.log", "/app/logs/app.log"],
        "docker_container": "mep-metadata-processor",
        "admin_ui": None
    },
    "embedding-processor": {
        "name": "Embedding Processor",
        "description": "Vector embedding generation service",
        "port": 8007,
        "url": "http://localhost:8007",
        "endpoints": ["/health", "/generate-embeddings", "/similarity"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/embedding-processor.log", "/app/logs/app.log"],
        "docker_container": "mep-embedding-processor",
        "admin_ui": None
    },
    "entity-processor": {
        "name": "Entity Processor",
        "description": "Entity extraction and relationship mapping",
        "port": 8008,
        "url": "http://localhost:8008",
        "endpoints": ["/health", "/extract-entities", "/relationships"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/entity-processor.log", "/app/logs/app.log"],
        "docker_container": "mep-entity-processor",
        "admin_ui": None
    },
    "processing-pipeline": {
        "name": "Processing Pipeline",
        "description": "Orchestrated document processing workflow",
        "port": 8003,
        "url": "http://localhost:8003",
        "endpoints": ["/health", "/pipeline/status", "/pipeline/start"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/processing-pipeline.log", "/app/logs/app.log"],
        "docker_container": "mep-processing-pipeline",
        "admin_ui": None
    },
    "queue-worker": {
        "name": "Queue Worker",
        "description": "Background job processor for guaranteed document processing",
        "port": None,
        "url": "http://localhost:8003",
        "endpoints": ["/process-queue-worker", "/queue/stats"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/queue-worker.log", "/app/logs/app.log"],
        "docker_container": "mep-queue-worker",
        "admin_ui": None
    },
    "status-worker": {
        "name": "Status Worker",
        "description": "Background status update processor for reliable status synchronization",
        "port": None,
        "url": "http://localhost:8003",
        "endpoints": ["/process-status-update", "/queue/stats"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/status-worker.log", "/app/logs/app.log"],
        "docker_container": "mep-status-worker",
        "admin_ui": None
    },
    "document-router": {
        "name": "Document Router",
        "description": "Intelligent document routing and analysis",
        "port": 8002,
        "url": "http://localhost:8002",
        "endpoints": ["/health", "/route", "/analyze"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/document-router.log", "/app/logs/app.log"],
        "docker_container": "mep-document-router",
        "admin_ui": None
    },
    "api-gateway": {
        "name": "API Gateway",
        "description": "Unified entry point for all client interactions",
        "port": 8000,
        "url": "http://localhost:8000",
        "endpoints": ["/health", "/api/v1/documents", "/api/v1/search"],
        "config_paths": ["/app/config/main.yaml"],
        "log_paths": ["/app/logs/api-gateway.log", "/app/logs/app.log"],
        "docker_container": "mep-api-gateway",
        "admin_ui": None
    },
    "elasticsearch": {
        "name": "Elasticsearch",
        "description": "Full-text search and content indexing",
        "port": 9200,
        "url": ELASTICSEARCH_URL,
        "endpoints": ["/_cluster/health", "/_cat/indices", "/_stats"],
        "config_paths": ["/usr/share/elasticsearch/config/elasticsearch.yml"],
        "log_paths": ["/usr/share/elasticsearch/logs/elasticsearch.log"],
        "docker_container": "mep-elasticsearch",
        "admin_ui": {
            "url": "http://localhost:5601",
            "name": "Kibana",
            "description": "Elasticsearch management and visualization"
        }
    },
    "qdrant": {
        "name": "Qdrant",
        "description": "Vector embeddings for semantic search",
        "port": 6333,
        "url": QDRANT_URL,
        "endpoints": ["/collections", "/health", "/metrics"],
        "config_paths": ["/qdrant/config/config.yaml"],
        "log_paths": ["/qdrant/logs/qdrant.log"],
        "docker_container": "mep-qdrant",
        "admin_ui": {
            "url": "http://localhost:7070/index.html",
            "name": "Qdrant UI",
            "description": "Vector database management interface"
        }
    },
    "neo4j": {
        "name": "Neo4j",
        "description": "Graph relationships and entity mapping",
        "port": 7474,
        "url": NEO4J_URL,
        "endpoints": ["/db/data/", "/browser/", "/metrics"],
        "config_paths": ["/conf/neo4j.conf"],
        "log_paths": ["/logs/neo4j.log", "/logs/debug.log"],
        "docker_container": "mep-neo4j",
        "admin_ui": {
            "url": "http://localhost:7474",
            "name": "Neo4j Browser",
            "description": "Graph database interface"
        }
    },
    "postgres": {
        "name": "PostgreSQL",
        "description": "Primary metadata database",
        "port": 5432,
        "url": "http://localhost:5432",
        "endpoints": ["/health"],
        "config_paths": ["/etc/postgresql/postgresql.conf"],
        "log_paths": ["/var/log/postgresql/postgresql.log"],
        "docker_container": "mep-postgres",
        "admin_ui": {
            "url": "http://localhost:8080",
            "name": "pgAdmin",
            "description": "PostgreSQL administration"
        }
    },
    "redis": {
        "name": "Redis",
        "description": "Caching and session management",
        "port": 6379,
        "url": "http://localhost:6379",
        "endpoints": ["/health"],
        "config_paths": ["/usr/local/etc/redis/redis.conf"],
        "log_paths": ["/var/log/redis/redis.log"],
        "docker_container": "mep-redis",
        "admin_ui": {
            "url": "http://localhost:8081",
            "name": "Redis Commander",
            "description": "Redis management interface"
        }
    },
    "minio": {
        "name": "MinIO",
        "description": "Object storage for files and embeddings",
        "port": 9000,
        "url": "http://localhost:9000",
        "endpoints": ["/minio/health/live", "/minio/health/ready"],
        "config_paths": ["/etc/minio/minio.conf"],
        "log_paths": ["/var/log/minio/minio.log"],
        "docker_container": "mep-minio",
        "admin_ui": {
            "url": "http://localhost:9001",
            "name": "MinIO Console",
            "description": "Object storage management interface"
        }
    },
    "flowise": {
        "name": "Flowise",
        "description": "LLM Flow Builder",
        "port": 3001,
        "url": "http://localhost:3001",
        "endpoints": ["/", "/api/v1/flows", "/api/v1/chatflows"],
        "config_paths": ["/usr/src/app/config/flowise.json"],
        "log_paths": ["/usr/src/app/logs/flowise.log"],
        "docker_container": "mep-flowise",
        "admin_ui": {
            "url": "http://localhost:3001",
            "name": "Flowise",
            "description": "LLM Flow Builder"
        }
    },
    "n8n": {
        "name": "n8n",
        "description": "Workflow automation platform",
        "port": 5678,
        "url": "http://localhost:5678",
        "endpoints": ["/", "/healthz", "/api/v1/workflows"],
        "config_paths": ["/home/node/.n8n/config"],
        "log_paths": ["/home/node/.n8n/logs"],
        "docker_container": "mep-n8n",
        "admin_ui": {
            "url": "http://localhost:5678",
            "name": "n8n Workflows",
            "description": "Workflow automation platform"
        }
    },
    "prometheus": {
        "name": "Prometheus",
        "description": "Metrics collection and monitoring",
        "port": 9090,
        "url": "http://localhost:9090",
        "endpoints": ["/", "/metrics", "/api/v1/status"],
        "config_paths": ["/etc/prometheus/prometheus.yml"],
        "log_paths": ["/prometheus/prometheus.log"],
        "docker_container": "mep-prometheus",
        "admin_ui": {
            "url": "http://localhost:9090",
            "name": "Prometheus",
            "description": "Metrics collection and monitoring"
        }
    },
    "grafana": {
        "name": "Grafana",
        "description": "Monitoring dashboards",
        "port": 3002,
        "url": "http://localhost:3002",
        "endpoints": ["/", "/api/health", "/api/datasources"],
        "config_paths": ["/etc/grafana/grafana.ini"],
        "log_paths": ["/var/log/grafana/grafana.log"],
        "docker_container": "mep-grafana",
        "admin_ui": {
            "url": "http://localhost:3002",
            "name": "Grafana",
            "description": "Monitoring dashboards"
        }
    },
    "qdrantui": {
        "name": "Qdrant UI",
        "description": "Vector database management interface",
        "port": 7070,
        "url": "http://localhost:7070",
        "endpoints": ["/"],
        "config_paths": [],
        "log_paths": [],
        "docker_container": None,
        "admin_ui": {
            "url": "http://localhost:7070/index.html",
            "name": "Qdrant UI",
            "description": "Vector database management interface"
        }
    }

}

# Service endpoints for health checks
SERVICES = {
    "core-processor": f"{CORE_PROCESSOR_URL}/health",
    "file-watcher": f"{FILE_WATCHER_URL}/health",
    "host-volume-manager": f"{HOST_VOLUME_MANAGER_URL}/health",
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
    "postgres": "http://localhost:5432",
    "redis": "http://localhost:6379",
    "minio": "http://localhost:9000/minio/health/live",
    "flowise": "http://localhost:3001/",
    "n8n": "http://localhost:5678/healthz",
    "prometheus": "http://localhost:9090/",
    "grafana": "http://localhost:3002/",
    "qdrantui": "http://localhost:7070/"
}

app = FastAPI(title="MDIS Dashboard", version="1.0.0")

# Mount static files and templates
# Determine the correct paths based on current working directory
import os
current_dir = os.getcwd()
print(f"Current working directory: {current_dir}")

# Check if we're in the mep_ainabox root directory
if current_dir.endswith('/mep_ainabox'):
    # Running from mep_ainabox root directory
    static_dir = "core/dashboard/static"
    templates_dir = "core/dashboard/templates"
elif current_dir.endswith('/dashboard'):
    # Running from dashboard directory
    static_dir = "static"
    templates_dir = "templates"
else:
    # Running from core directory
    static_dir = "dashboard/static"
    templates_dir = "dashboard/templates"

print(f"Static directory: {static_dir}")
print(f"Templates directory: {templates_dir}")

# Verify the directories exist
if not os.path.exists(static_dir):
    print(f"Warning: Static directory does not exist: {static_dir}")
if not os.path.exists(templates_dir):
    print(f"Warning: Templates directory does not exist: {templates_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# List all HTML templates in the templates directory
try:
    template_files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
    print(f"Available HTML templates in '{templates_dir}': {template_files}")
except Exception as e:
    print(f"Error listing templates in '{templates_dir}': {e}")


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

class ConfigurationItem(BaseModel):
    key: str
    value: str
    description: str
    category: str
    is_sensitive: bool = False
    is_required: bool = True

class ServiceDetail(BaseModel):
    name: str
    status: str
    url: str
    port: int
    description: str
    service_key: Optional[str] = None
    configuration: List[ConfigurationItem]
    logs: List[str]
    metrics: Dict[str, Any]
    admin_ui: Optional[Dict[str, str]] = None

class AdminStatus(BaseModel):
    infrastructure_running: bool
    core_system_running: bool
    startup_in_progress: bool
    startup_logs: List[str]
    shutdown_in_progress: bool
    shutdown_logs: List[str]
    last_update: datetime

# Scan Folder Models
class ScanFolderRequest(BaseModel):
    folder_path: str
    processing_mode: str = "enhanced"
    concurrent_limit: int = 5
    max_depth: int = 10
    recursive: bool = True
    save_report: bool = False

class ScanFileStatus(BaseModel):
    filename: str
    relative_path: str
    status: str  # pending, processing, completed, failed, skipped
    file_size: int
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None

class ScanLogEntry(BaseModel):
    timestamp: datetime
    level: str  # info, success, warning, error
    message: str

class ScanExecution(BaseModel):
    id: str
    folder_path: str
    processing_mode: str
    concurrent_limit: int
    max_depth: int
    recursive: bool
    save_report: bool
    status: str  # pending, running, completed, failed, stopped
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    progress: float = 0.0
    files: List[ScanFileStatus] = []
    logs: List[ScanLogEntry] = []

# Global admin state
admin_state = {
    "startup_in_progress": False,
    "startup_logs": [],
    "startup_thread": None,
    "shutdown_in_progress": False,
    "shutdown_logs": [],
    "shutdown_thread": None
}

# Scan folder execution storage
scan_executions: Dict[str, ScanExecution] = {}
scan_processes: Dict[str, subprocess.Popen] = {}

async def check_service_health(service_name: str, url: str) -> ServiceHealth:
    """Check health of a single service"""
    start_time = datetime.now()
    
    # Handle database services that don't have HTTP endpoints
    if service_name in ["postgres", "redis"]:
        try:
            # Extract port from URL for database services
            if service_name == "postgres":
                port = 5432
            elif service_name == "redis":
                port = 6379
            else:
                port = 5432  # Default fallback
            
            # Check port connectivity
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            if result == 0:
                return ServiceHealth(
                    service=service_name,
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.now(),
                    details={"port": port, "connection": "successful"}
                )
            else:
                return ServiceHealth(
                    service=service_name,
                    status="unhealthy",
                    response_time=response_time,
                    last_check=datetime.now(),
                    details={"port": port, "connection": "failed", "error_code": result}
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
    
    # Handle HTTP services
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
            
            # Consider both 200 (OK) and 302 (Found/Redirect) as healthy
            # Many services redirect to their main page or login
            if response.status_code in [200, 302]:
                details = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                return ServiceHealth(
                    service=service_name,
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.now(),
                    details={"status_code": response.status_code, "redirect": response.status_code == 302}
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
                # Don't log errors for services that aren't running yet
                return []
    except Exception as e:
        # Don't log errors for services that aren't running yet
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
        # Don't log errors for services that aren't running yet
        return {"total_documents": 0, "indices": []}

def load_configuration() -> Dict:
    """Load configuration from file or create default"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default configuration
            save_configuration(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG

def save_configuration(config: Dict):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")

async def get_service_logs(service_name: str, lines: int = 50) -> List[str]:
    """Get recent logs for a service"""
    try:
        service_info = SERVICE_INFO.get(service_name, {})
        docker_container = service_info.get("docker_container")
        
        # First try to get logs from Docker container (most reliable)
        if docker_container:
            try:
                result = subprocess.run(
                    ["docker", "logs", docker_container, "--tail", str(lines)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip().split('\n')
                else:
                    logger.warning(f"Docker logs command failed for {docker_container}: {result.stderr}")
            except Exception as e:
                logger.warning(f"Error getting Docker logs for {docker_container}: {e}")
        else:
            # For services without Docker containers, try to get process logs
            logger.debug(f"No Docker container for {service_name}, trying alternative log sources")
        
        # Fallback to local log files
        log_paths = service_info.get("log_paths", [])
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        lines_list = f.readlines()
                        return lines_list[-lines:] if len(lines_list) > lines else lines_list
                except Exception as e:
                    logger.warning(f"Error reading log file {log_path}: {e}")
            else:
                logger.warning(f"Log file not found at {log_path}")
        
        # Try alternative log locations
        alternative_logs = [
            f"logs/{service_name}.log",
            f"logs/app.log",
            f"../logs/{service_name}.log",
            f"../logs/app.log"
        ]
        
        for alt_log in alternative_logs:
            if os.path.exists(alt_log):
                try:
                    with open(alt_log, 'r') as f:
                        lines_list = f.readlines()
                        return lines_list[-lines:] if len(lines_list) > lines else lines_list
                except Exception as e:
                    logger.warning(f"Error reading alternative log file {alt_log}: {e}")
        
        if docker_container:
            return [f"No logs available for {service_name}. Try checking Docker logs manually: docker logs {docker_container}"]
        else:
            return [f"No logs available for {service_name}. This service runs outside of Docker."]
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return [f"Error retrieving logs: {str(e)}"]

async def get_service_metrics(service_name: str) -> Dict[str, Any]:
    """Get metrics for a service"""
    try:
        service_info = SERVICE_INFO.get(service_name, {})
        service_url = service_info.get("url", "")
        
        if not service_url:
            return {"error": "Service URL not found"}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {}
            if service_name == "qdrant":
                headers["api-key"] = QDRANT_API_KEY
            
            # Try different metrics endpoints based on service type
            metrics_endpoints = [
                "/metrics",
                "/health",
                "/stats",
                "/status",
                "/_cluster/health",  # Elasticsearch
                "/collections",      # Qdrant
                "/db/data/"          # Neo4j
            ]
            
            for endpoint in metrics_endpoints:
                try:
                    full_url = service_url + endpoint
                    response = await client.get(full_url, headers=headers, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw_response": response.text}
                        return data
                except Exception as e:
                    logger.debug(f"Failed to get metrics from {endpoint} for {service_name}: {e}")
                    continue
            
            # If no metrics endpoint works, try to get basic service info
            try:
                # Get Docker container stats
                docker_container = service_info.get("docker_container")
                if docker_container:
                    result = subprocess.run(
                        ["docker", "stats", docker_container, "--no-stream", "--format", "json"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        import json
                        stats = json.loads(result.stdout.strip())
                        return {
                            "container_stats": stats,
                            "service_info": {
                                "name": service_info.get("name", service_name),
                                "port": service_info.get("port", "N/A"),
                                "description": service_info.get("description", "")
                            }
                        }
                else:
                    # For services without Docker containers, return basic service info
                    return {
                        "service_info": {
                            "name": service_info.get("name", service_name),
                            "port": service_info.get("port", "N/A"),
                            "description": service_info.get("description", ""),
                            "note": "This service runs outside of Docker"
                        }
                    }
            except Exception as e:
                logger.debug(f"Failed to get Docker stats for {service_name}: {e}")
            
            return {"error": f"Unable to retrieve metrics for {service_name}"}
    except Exception as e:
        logger.error(f"Error getting metrics for {service_name}: {e}")
        return {"error": str(e)}

async def get_service_configuration(service_name: str) -> List[ConfigurationItem]:
    """Get configuration for a specific service"""
    try:
        service_info = SERVICE_INFO.get(service_name, {})
        config_items = []
        
        # Get global configuration
        global_config = load_configuration()
        for category, items in global_config.items():
            for item in items:
                if service_name in item.get("key", "").lower() or service_name in item.get("description", "").lower():
                    config_items.append(ConfigurationItem(**item))
        
        # Try to get service-specific configuration files
        config_paths = service_info.get("config_paths", [])
        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        content = f.read()
                        config_items.append(ConfigurationItem(
                            key=f"config_file_{os.path.basename(config_path)}",
                            value=content[:500] + "..." if len(content) > 500 else content,
                            description=f"Configuration file: {config_path}",
                            category="service_config",
                            is_sensitive=False
                        ))
                else:
                    # Try to get config from Docker container
                    docker_container = service_info.get("docker_container")
                    if docker_container:
                        result = subprocess.run(
                            ["docker", "exec", docker_container, "cat", config_path],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            content = result.stdout
                            config_items.append(ConfigurationItem(
                                key=f"config_file_{os.path.basename(config_path)}",
                                value=content[:500] + "..." if len(content) > 500 else content,
                                description=f"Configuration file from container: {config_path}",
                                category="service_config",
                                is_sensitive=False
                            ))
            except Exception as e:
                logger.debug(f"Failed to read config file {config_path} for {service_name}: {e}")
        
        # Add service environment variables
        docker_container = service_info.get("docker_container")
        if docker_container:
            try:
                result = subprocess.run(
                    ["docker", "inspect", docker_container, "--format", "{{range .Config.Env}}{{.}}{{\"\\n\"}}{{end}}"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    env_vars = result.stdout.strip().split('\n')
                    for env_var in env_vars[:10]:  # Limit to first 10 env vars
                        if '=' in env_var:
                            key, value = env_var.split('=', 1)
                            config_items.append(ConfigurationItem(
                                key=key,
                                value=value if not any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']) else '••••••••',
                                description=f"Environment variable",
                                category="environment",
                                is_sensitive=any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token'])
                            ))
            except Exception as e:
                logger.debug(f"Failed to get environment variables for {service_name}: {e}")
        
        return config_items
    except Exception as e:
        logger.error(f"Error getting configuration for {service_name}: {e}")
        return []

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
        # Don't log errors for services that aren't running yet
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

# Scan Folder Functions
def add_scan_log(execution_id: str, level: str, message: str):
    """Add a log entry to a scan execution"""
    if execution_id in scan_executions:
        log_entry = ScanLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message
        )
        scan_executions[execution_id].logs.append(log_entry)

def update_scan_progress(execution_id: str):
    """Update progress percentage for a scan execution"""
    if execution_id in scan_executions:
        execution = scan_executions[execution_id]
        if execution.total_files > 0:
            execution.progress = (execution.processed_files / execution.total_files) * 100
        else:
            execution.progress = 0.0

async def scan_folder_worker(execution_id: str, request: ScanFolderRequest):
    """Background worker for scanning folders with dynamic volume mounting"""
    # Store original directory - we'll restore this at the end
    import os
    original_dir = os.getcwd()
    
    try:
        execution = scan_executions[execution_id]
        execution.status = "running"
        add_scan_log(execution_id, "info", f"Starting scan of folder: {request.folder_path}")
        
        # Change to project root for Docker operations
        project_root = "/home/lie/repo_mep/mep_ainabox"
        os.chdir(project_root)
        
        # Check if folder exists and is accessible
        if not os.path.exists(request.folder_path):
            raise Exception(f"Folder does not exist: {request.folder_path}")
        
        if not os.path.isdir(request.folder_path):
            raise Exception(f"Path is not a directory: {request.folder_path}")
        
        # Resolve absolute path
        folder_path = os.path.abspath(request.folder_path)
        add_scan_log(execution_id, "info", f"Resolved folder path: {folder_path}")
        
        # Use the volume manager to dynamically mount the folder
        add_scan_log(execution_id, "info", f"Mounting folder to shared volume: {folder_path}")
        
        # Call the volume manager to mount the folder
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                mount_response = await client.post(
                    f"{HOST_VOLUME_MANAGER_URL}/mount",
                    json={
                        "host_path": folder_path,
                        "folder_name": f"scan_{execution_id[:8]}"
                    },
                    timeout=30.0
                )
                
                if mount_response.status_code != 200:
                    raise Exception(f"Failed to mount folder: {mount_response.text}")
                
                mount_data = mount_response.json()
                if not mount_data.get("success"):
                    raise Exception(f"Volume manager failed to mount folder: {mount_data.get('error_message')}")
                
                unique_folder_name = mount_data.get("unique_folder_name")
                add_scan_log(execution_id, "info", f"Successfully mounted folder: {unique_folder_name}")
                
        except Exception as e:
            add_scan_log(execution_id, "error", f"Failed to mount folder using volume manager: {str(e)}")
            add_scan_log(execution_id, "info", "Falling back to direct folder access")
            unique_folder_name = None
        
        # Use dynamic Docker mounting approach for external folders
        # This ensures the processing pipeline can access the files correctly
        container_name = f"mep-folder-scanner-{execution_id[:8]}"
        
        # Check if Docker image exists, if not build it
        try:
            result = subprocess.run(
                ["docker", "images", "-q", "mep-file-watcher:latest"],
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            if not result.stdout.strip():
                add_scan_log(execution_id, "info", "Docker image not found, building mep-file-watcher:latest...")
                build_result = subprocess.run(
                    ["docker", "build", "-t", "mep-file-watcher:latest", "-f", "./core/file_watcher/Dockerfile", "./core"],
                    capture_output=True,
                    text=True,
                    timeout=300.0  # 5 minutes timeout for build
                )
                
                if build_result.returncode != 0:
                    raise Exception(f"Failed to build Docker image: {build_result.stderr}")
                
                add_scan_log(execution_id, "info", "Docker image built successfully")
                
            # Use Docker with volume manager if available
            if unique_folder_name:
                add_scan_log(execution_id, "info", f"Executing Docker command: docker run --rm --name {container_name} --network host -v shared_scan_folders:/app/scan_folders:ro -e CORE_PROCESSOR_URL=http://localhost:8001 -e HOST_SCAN_FOLDER_PATH={folder_path} mep-file-watcher:latest python3 /app/folder_scanner.py /app/scan_folders --queue --save-report scan_report_{execution_id}.json")
                
                # Build Docker command with volume manager
                docker_cmd = [
                    "docker", "run", "--rm",
                    "--name", container_name,
                    "--network", "host",
                    "-v", "shared_scan_folders:/app/scan_folders:ro",
                    "-e", f"CORE_PROCESSOR_URL=http://localhost:8001",
                    "-e", f"HOST_SCAN_FOLDER_PATH={folder_path}",
                    "mep-file-watcher:latest",
                    "python3", "/app/folder_scanner.py", "/app/scan_folders",
                    "--queue"
                ]
                
                # Add processing mode
                if request.processing_mode == "sync":
                    docker_cmd.append("--sync")
                
                # Add other options
                if not request.recursive:
                    docker_cmd.append("--no-recursive")
                
                if request.max_depth != 10:
                    docker_cmd.extend(["--max-depth", str(request.max_depth)])
                
                if request.concurrent_limit != 5:
                    docker_cmd.extend(["--concurrent", str(request.concurrent_limit)])
                
                if request.save_report:
                    # Generate a timestamped report filename
                    import time
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    report_filename = f"scan_report_{timestamp}.json"
                    docker_cmd.extend(["--save-report", report_filename])
                
                add_scan_log(execution_id, "info", f"Process started with PID: {os.getpid()}")
                
                # Start the Docker process
                process = subprocess.Popen(
                    docker_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                scan_processes[execution_id] = process
                
                # Monitor the process
                import threading
                
                def monitor_stderr():
                    while True:
                        error_output = process.stderr.readline()
                        if error_output == '' and process.poll() is not None:
                            break
                        if error_output:
                            line = error_output.strip()
                            # Check if it's actually an error or just info output
                            if "ERROR" in line:
                                add_scan_log(execution_id, "error", f"STDERR: {line}")
                            else:
                                add_scan_log(execution_id, "info", f"STDERR: {line}")
                
                # Start stderr monitoring in a separate thread
                stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
                stderr_thread.start()
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        add_scan_log(execution_id, "info", line)
                        
                        # Parse progress from output
                        if "Found" in line and "files to process" in line:
                            try:
                                total_files = int(line.split()[1])
                                execution.total_files = total_files
                                add_scan_log(execution_id, "info", f"Found {total_files} files to process")
                            except:
                                pass
                        elif "Uploaded file" in line or "✅ Uploaded file" in line:
                            execution.processed_files += 1
                            update_scan_progress(execution_id)
                        elif "Successfully processed" in line or "✅ Successfully processed" in line:
                            execution.completed_files += 1
                        elif "Failed to process" in line or "❌ Failed to process" in line:
                            execution.failed_files += 1
                        elif "Processing file" in line:
                            # Extract file number from "Processing file X/Y: filename"
                            try:
                                parts = line.split("Processing file ")[1].split("/")[0]
                                current_file = int(parts)
                                if execution.total_files == 0:
                                    execution.total_files = current_file
                            except:
                                pass
                
                # Get return code
                return_code = process.poll()
                
                if return_code == 0:
                    execution.status = "completed"
                    add_scan_log(execution_id, "success", "Scan completed successfully")
                else:
                    execution.status = "failed"
                    add_scan_log(execution_id, "error", f"Scan failed with return code: {return_code}")
                
                execution.completed_at = datetime.utcnow()
                return
                
        except Exception as e:
            add_scan_log(execution_id, "warning", f"Docker not available, falling back to direct execution: {str(e)}")
            # Fall back to direct Python execution
            add_scan_log(execution_id, "info", "Using direct Python execution (files may not be accessible to processing pipeline)")
            
            # Build the scan command for direct execution
            cmd = [
                "python3", 
                "./core/file_watcher/folder_scanner.py",
                folder_path
            ]
            
            # Add processing mode
            if request.processing_mode == "queue":
                cmd.append("--queue")
            elif request.processing_mode == "sync":
                cmd.append("--sync")
            
            # Add other options
            if not request.recursive:
                cmd.append("--no-recursive")
            
            if request.max_depth != 10:
                cmd.extend(["--max-depth", str(request.max_depth)])
            
            if request.concurrent_limit != 5:
                cmd.extend(["--concurrent", str(request.concurrent_limit)])
            
            if request.save_report:
                # Generate a timestamped report filename
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                report_filename = f"scan_report_{timestamp}.json"
                cmd.extend(["--save-report", report_filename])
            
            add_scan_log(execution_id, "info", f"Executing direct command: {' '.join(cmd)}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            add_scan_log(execution_id, "info", f"Process started with PID: {process.pid}")
            scan_processes[execution_id] = process
            
            # Continue with monitoring (skip the Docker-specific code below)
            import threading
            
            def monitor_stderr():
                while True:
                    error_output = process.stderr.readline()
                    if error_output == '' and process.poll() is not None:
                        break
                    if error_output:
                        line = error_output.strip()
                        # Check if it's actually an error or just info output
                        if "ERROR" in line:
                            add_scan_log(execution_id, "error", f"STDERR: {line}")
                        else:
                            add_scan_log(execution_id, "info", f"STDERR: {line}")
            
            # Start stderr monitoring in a separate thread
            stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
            stderr_thread.start()
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    add_scan_log(execution_id, "info", line)
                    
                    # Parse progress from output
                    if "Found" in line and "files to process" in line:
                        try:
                            total_files = int(line.split()[1])
                            execution.total_files = total_files
                            add_scan_log(execution_id, "info", f"Found {total_files} files to process")
                        except:
                            pass
                    elif "Uploaded file" in line or "✅ Uploaded file" in line:
                        execution.processed_files += 1
                        update_scan_progress(execution_id)
                    elif "Successfully processed" in line or "✅ Successfully processed" in line:
                        execution.completed_files += 1
                    elif "Failed to process" in line or "❌ Failed to process" in line:
                        execution.failed_files += 1
                    elif "Processing file" in line:
                        # Extract file number from "Processing file X/Y: filename"
                        try:
                            parts = line.split("Processing file ")[1].split("/")[0]
                            current_file = int(parts)
                            if execution.total_files == 0:
                                execution.total_files = current_file
                        except:
                            pass
            
            # Get return code
            return_code = process.poll()
            
            if return_code == 0:
                execution.status = "completed"
                add_scan_log(execution_id, "success", "Scan completed successfully")
            else:
                execution.status = "failed"
                add_scan_log(execution_id, "error", f"Scan failed with return code: {return_code}")
            
            execution.completed_at = datetime.utcnow()
            return
            
    except Exception as e:
        if execution_id in scan_executions:
            scan_executions[execution_id].status = "failed"
            add_scan_log(execution_id, "error", f"Scan worker error: {str(e)}")
            scan_executions[execution_id].completed_at = datetime.utcnow()
            if execution_id in scan_processes:
                del scan_processes[execution_id]
    
    finally:
        # Always restore original directory, regardless of success or failure
        try:
            os.chdir(original_dir)
            logger.info(f"Restored working directory to: {original_dir}")
        except:
            pass

def stop_scan_execution(execution_id: str):
    """Stop a running scan execution"""
    if execution_id in scan_executions and execution_id in scan_processes:
        execution = scan_executions[execution_id]
        process = scan_processes[execution_id]
        if execution.status == "running":
            process.terminate()
            execution.status = "stopped"
            execution.completed_at = datetime.now()
            add_scan_log(execution_id, "warning", "Scan execution stopped by user")
            del scan_processes[execution_id]
            return True
    return False

def clear_completed_executions():
    """Clear completed, failed, and stopped executions"""
    global scan_executions, scan_processes
    to_remove = []
    for execution_id, execution in scan_executions.items():
        if execution.status in ["completed", "failed", "stopped"]:
            to_remove.append(execution_id)
    
    for execution_id in to_remove:
        del scan_executions[execution_id]
        if execution_id in scan_processes:
            del scan_processes[execution_id]
    
    return len(to_remove)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    print("Dashboard page requested")
    print(f"Templates directory: {templates_dir}")
    print(f"Templates loaded in Jinja2Templates: {templates.env.list_templates()}")
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

@app.get("/configuration", response_class=HTMLResponse)
async def configuration_page(request: Request):
    """Configuration management page"""
    return templates.TemplateResponse("configuration.html", {"request": request})

@app.get("/api/configuration")
async def get_configuration():
    """Get current configuration"""
    config = load_configuration()
    return config

@app.post("/api/configuration")
async def update_configuration(request: Request):
    """Update configuration"""
    try:
        config_data = await request.json()
        save_configuration(config_data)
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating configuration: {str(e)}")

@app.get("/service/{service_name}", response_class=HTMLResponse)
async def service_detail_page(request: Request, service_name: str):
    """Service detail page"""
    return templates.TemplateResponse("service_detail.html", {"request": request, "service_name": service_name})

@app.get("/api/service/{service_name}")
async def get_service_detail(service_name: str):
    """Get detailed information about a specific service"""
    try:
        service_info = SERVICE_INFO.get(service_name, {})
        if not service_info:
            raise HTTPException(status_code=404, detail="Service not found")
        
        logger.info(f"Getting details for service: {service_name}")
        
        # Get service health
        health_url = SERVICES.get(service_name, "")
        health = await check_service_health(service_name, health_url)
        logger.info(f"Health status for {service_name}: {health.status}")
        
        # Get service logs
        logs = await get_service_logs(service_name)
        logger.info(f"Retrieved {len(logs)} log lines for {service_name}")
        
        # Get service metrics
        metrics = await get_service_metrics(service_name)
        logger.info(f"Retrieved metrics for {service_name}: {list(metrics.keys()) if isinstance(metrics, dict) else 'error'}")
        
        # Get service-specific configuration
        service_config = await get_service_configuration(service_name)
        logger.info(f"Retrieved {len(service_config)} configuration items for {service_name}")
        
        # Map service name to service key
        service_key_mapping = {
            "api-gateway": "api-gateway",
            "core-processor": "core-processor", 
            "document-router": "document-router",
            "processing-pipeline": "processing-pipeline",
            "storage-manager": "storage-manager",
            "text-processor": "text-processor",
            "metadata-processor": "metadata-processor",
            "embedding-processor": "embedding-processor",
            "entity-processor": "entity-processor",
            "file-watcher": "file-watcher",
            "ollama": "ollama",
            "postgres": "postgres",
            "elasticsearch": "elasticsearch",
            "qdrant": "qdrant",
            "redis": "redis",
            "minio": "minio",
            "neo4j": "neo4j",
            "pgadmin": "pgadmin",
            "redis-commander": "redis-commander",
            "kibana": "kibana",
            "flowise": "flowise",
            "n8n": "n8n",
            "prometheus": "prometheus",
            "grafana": "grafana",
            "qdrantui": "qdrantui"
        }
        
        service_key = service_key_mapping.get(service_name)
        
        service_detail = ServiceDetail(
            name=service_info.get("name", service_name),
            status=health.status,
            url=service_info.get("url", ""),
            port=service_info.get("port", 0),
            description=service_info.get("description", ""),
            service_key=service_key,
            configuration=service_config,
            logs=logs,
            metrics=metrics,
            admin_ui=service_info.get("admin_ui")
        )
        
        return service_detail
    except Exception as e:
        logger.error(f"Error getting service details for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting service details: {str(e)}")

@app.get("/api/service/{service_name}/logs")
async def get_service_logs_api(service_name: str, lines: int = 50):
    """Get logs for a specific service"""
    try:
        logs = await get_service_logs(service_name, lines)
        return {"service": service_name, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service logs: {str(e)}")

@app.get("/api/service/{service_name}/metrics")
async def get_service_metrics_api(service_name: str):
    """Get metrics for a specific service"""
    try:
        metrics = await get_service_metrics(service_name)
        return {"service": service_name, "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service metrics: {str(e)}")

@app.get("/api/service/{service_name}/configuration")
async def get_service_configuration_api(service_name: str):
    """Get configuration for a specific service"""
    try:
        config = await get_service_configuration(service_name)
        return {"service": service_name, "configuration": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service configuration: {str(e)}")

# Admin functions
def check_infrastructure_services() -> bool:
    """Check if infrastructure services are running"""
    try:
        # Check key infrastructure services
        services_to_check = [
            ("postgres", 5432),
            ("elasticsearch", 9200),
            ("qdrant", 6333),
            ("redis", 6379)
        ]
        
        for service_name, port in services_to_check:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", port))
                sock.close()
                if result != 0:
                    return False
            except:
                return False
        return True
    except:
        return False

def check_core_services() -> bool:
    """Check if core services are running (Native Host-based Processing)"""
    try:
        # Check key core services with correct ports for native processing
        services_to_check = [
            ("api-gateway", 8011, "/health"),  # API Gateway runs on port 8011 with native processing
            ("core-processor", 8001, "/docs"),  # Core processor responds on /docs
            ("file-watcher", 8009, "/health"),
            ("processing-pipeline", 8003, "/health")  # Processing pipeline for queue/status workers
        ]
        
        for service_name, port, endpoint in services_to_check:
            try:
                # First check if port is open
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", port))
                sock.close()
                
                if result != 0:
                    logger.warning(f"Core service {service_name} not responding on port {port}")
                    return False
                
                # If port is open, try HTTP request for better verification
                try:
                    import httpx
                    with httpx.Client(timeout=3.0) as client:
                        response = client.get(f"http://localhost:{port}{endpoint}")
                        if response.status_code not in [200, 302, 404]:  # 404 is OK for some endpoints
                            logger.warning(f"Core service {service_name} returned status {response.status_code}")
                            return False
                except Exception as http_error:
                    # HTTP request failed, but port is open, so service might be starting
                    logger.debug(f"HTTP check failed for {service_name} on port {port}: {http_error}")
                    # Don't fail here, just log it
                    
            except Exception as e:
                logger.warning(f"Error checking {service_name} on port {port}: {e}")
                return False
        return True
    except Exception as e:
        logger.error(f"Error in check_core_services: {e}")
        return False

def startup_services():
    """Start all services in the background"""
    def startup_worker():
        admin_state["startup_in_progress"] = True
        admin_state["startup_logs"] = []
        
        # Store the original working directory
        original_dir = os.getcwd()
        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting MEP AI NABOX services...")
        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Original directory: {original_dir}")
        
        try:
            # Step 1: Start infrastructure services
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 Starting infrastructure services...")
            
            # Try to find the services directory
            # Since the dashboard is now running on the host, we need to navigate to the project root
            # The dashboard is in core/dashboard, so we need to go up two levels to reach the project root
            # Current: /home/lie/repo_mep/mep_ainabox/core/dashboard
            # Need: /home/lie/repo_mep/mep_ainabox/services
            project_root = os.path.dirname(os.path.dirname(original_dir))
            services_dir = os.path.join(project_root, 'services')
            
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for services directory: {services_dir}")
            
            if os.path.exists(services_dir):
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found services directory")
                os.chdir(services_dir)
                result = subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Infrastructure services started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to start infrastructure services: {result.stderr}")
                    admin_state["startup_in_progress"] = False
                    return
            else:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Services directory not found: {services_dir}")
                admin_state["startup_in_progress"] = False
                return
            
            # Wait for infrastructure services to be ready
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Waiting for infrastructure services to be ready...")
            time.sleep(30)
            
            # Step 2: Start core services (Native Host-based Processing)
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Starting native core system services...")
            
            # Navigate to the core directory (where the start_native_services.sh script is)
            # Since the dashboard is now running on the host, we need to go up one level from core/dashboard
            core_dir = os.path.dirname(original_dir)
            
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for core directory: {core_dir}")
            
            if os.path.exists(core_dir):
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found core directory")
                os.chdir(core_dir)
                
                # Start native services using the start_native_services.sh script
                result = subprocess.run(
                    ["./start_native_services.sh", "--start", "all"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Native core system services started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to start native core services: {result.stderr}")
                    admin_state["startup_in_progress"] = False
                    return
            else:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Core directory not found: {core_dir}")
                admin_state["startup_in_progress"] = False
                return
            
            # Wait for core services to be ready
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Waiting for core services to be ready...")
            time.sleep(30)
            
            # Final status check
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Performing final health checks...")
            
            if check_infrastructure_services():
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Infrastructure services are healthy")
            else:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Infrastructure services may have issues")
            
            if check_core_services():
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Core services are healthy")
            else:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Core services may have issues")
            
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 MEP AI NABOX startup completed!")
            
        except Exception as e:
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Startup failed with error: {str(e)}")
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_dir)
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Restored working directory to: {original_dir}")
            except Exception as e:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to restore working directory: {str(e)}")
            admin_state["startup_in_progress"] = False
    
    # Start the worker thread
    if not admin_state["startup_in_progress"]:
        admin_state["startup_thread"] = threading.Thread(target=startup_worker, daemon=True)
        admin_state["startup_thread"].start()

def startup_admin_ui_services():
    """Start admin UI services in the background"""
    def startup_ui_worker():
        admin_state["startup_in_progress"] = True
        admin_state["startup_logs"] = []
        
        # Store the original working directory
        original_dir = os.getcwd()
        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️ Starting Admin UI services...")
        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Original directory: {original_dir}")
        
        try:
            # Navigate to the services directory
            project_root = os.path.dirname(os.path.dirname(original_dir))
            services_dir = os.path.join(project_root, 'services')
            
            if os.path.exists(services_dir):
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found services directory")
                os.chdir(services_dir)
                
                # Step 1: Start Qdrant UI service using daemon script
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Starting Qdrant UI...")
                
                # Use the new daemon script
                qdrant_ui_daemon_script = os.path.join(services_dir, 'scripts', 'start-qdrant-ui-daemon.sh')
                if os.path.exists(qdrant_ui_daemon_script):
                    try:
                        # Make script executable
                        os.chmod(qdrant_ui_daemon_script, 0o755)
                        
                        # Run the daemon script
                        result = subprocess.run(
                            ["bash", qdrant_ui_daemon_script],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if result.returncode == 0:
                            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Qdrant UI started successfully")
                            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Logs available at: {os.path.join(services_dir, 'qdrant-ui.log')}")
                        else:
                            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Qdrant UI startup had issues: {result.stderr}")
                            if result.stdout:
                                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Output: {result.stdout}")
                    except subprocess.TimeoutExpired:
                        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Qdrant UI startup timed out")
                    except Exception as e:
                        admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Qdrant UI startup failed: {str(e)}")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Qdrant UI daemon script not found: {qdrant_ui_daemon_script}")
                
                # Step 2: Start monitoring services with profile
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Starting monitoring services (Prometheus & Grafana)...")
                result = subprocess.run(
                    ["docker", "compose", "--profile", "monitoring", "up", "-d", "prometheus", "grafana"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Monitoring services started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Monitoring services startup had issues: {result.stderr}")
                
                # Step 3: Start development profile services
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛠️ Starting development UI services...")
                
                # Start pgAdmin (development profile)
                result = subprocess.run(
                    ["docker", "compose", "--profile", "dev", "up", "-d", "pgadmin"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ pgAdmin started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ pgAdmin startup had issues: {result.stderr}")
                
                # Start Redis Commander (development profile)
                result = subprocess.run(
                    ["docker", "compose", "--profile", "dev", "up", "-d", "redis-commander"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Redis Commander started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Redis Commander startup had issues: {result.stderr}")
                
                # Step 4: Start regular services (no profile needed)
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Starting regular admin UI services...")
                
                # Start MinIO (has built-in console on port 9001)
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "minio"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ MinIO Console started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ MinIO Console startup had issues: {result.stderr}")
                
                # Start Kibana
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "kibana"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Kibana started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Kibana startup had issues: {result.stderr}")
                
                # Start Flowise
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "flowise"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Flowise started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Flowise startup had issues: {result.stderr}")
                
                # Start n8n
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "n8n"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ n8n started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ n8n startup had issues: {result.stderr}")
                
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Admin UI services startup completed!")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Available Admin UIs:")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Qdrant UI: http://localhost:7070/index.html")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Grafana: http://localhost:3002")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Prometheus: http://localhost:9090")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • MinIO Console: http://localhost:9001")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Kibana: http://localhost:5601")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • pgAdmin: http://localhost:8080")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Redis Commander: http://localhost:8081")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • Flowise: http://localhost:3001")
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}]   • n8n: http://localhost:5678")
                
            else:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Services directory not found: {services_dir}")
                admin_state["startup_in_progress"] = False
                return
            
        except Exception as e:
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Admin UI startup failed with error: {str(e)}")
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_dir)
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Restored working directory to: {original_dir}")
            except Exception as e:
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to restore working directory: {str(e)}")
            admin_state["startup_in_progress"] = False
    
    # Start the worker thread
    if not admin_state["startup_in_progress"]:
        admin_state["startup_thread"] = threading.Thread(target=startup_ui_worker, daemon=True)
        admin_state["startup_thread"].start()

def stop_admin_ui_services():
    """Stop admin UI services in the background"""
    def stop_ui_worker():
        admin_state["shutdown_in_progress"] = True
        admin_state["shutdown_logs"] = []
        
        # Store the original working directory
        original_dir = os.getcwd()
        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Stopping Admin UI services...")
        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Original directory: {original_dir}")
        
        try:
            # Navigate to the services directory
            project_root = os.path.dirname(os.path.dirname(original_dir))
            services_dir = os.path.join(project_root, 'services')
            
            if os.path.exists(services_dir):
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found services directory")
                os.chdir(services_dir)
                
                # Step 1: Stop Qdrant UI service using daemon script
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Stopping Qdrant UI...")
                
                # Use the stop daemon script
                qdrant_ui_stop_script = os.path.join(services_dir, 'scripts', 'stop-qdrant-ui-daemon.sh')
                if os.path.exists(qdrant_ui_stop_script):
                    try:
                        # Make script executable
                        os.chmod(qdrant_ui_stop_script, 0o755)
                        
                        # Run the stop daemon script
                        result = subprocess.run(
                            ["bash", qdrant_ui_stop_script],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if result.returncode == 0:
                            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Qdrant UI stopped successfully")
                        else:
                            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Qdrant UI stop had issues: {result.stderr}")
                            if result.stdout:
                                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Output: {result.stdout}")
                    except subprocess.TimeoutExpired:
                        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Qdrant UI stop timed out")
                    except Exception as e:
                        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Qdrant UI stop failed: {str(e)}")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Qdrant UI stop script not found: {qdrant_ui_stop_script}")
                
                # Step 2: Stop monitoring services
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Stopping monitoring services (Prometheus & Grafana)...")
                result = subprocess.run(
                    ["docker", "compose", "--profile", "monitoring", "stop", "prometheus", "grafana"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Monitoring services stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Monitoring services stop had issues: {result.stderr}")
                
                # Step 3: Stop development profile services
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛠️ Stopping development UI services...")
                
                # Stop pgAdmin (development profile)
                result = subprocess.run(
                    ["docker", "compose", "--profile", "dev", "stop", "pgadmin"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ pgAdmin stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ pgAdmin stop had issues: {result.stderr}")
                
                # Stop Redis Commander (development profile)
                result = subprocess.run(
                    ["docker", "compose", "--profile", "dev", "stop", "redis-commander"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Redis Commander stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Redis Commander stop had issues: {result.stderr}")
                
                # Step 4: Stop regular services (no profile needed)
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Stopping regular admin UI services...")
                
                # Stop MinIO
                result = subprocess.run(
                    ["docker", "compose", "stop", "minio"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ MinIO Console stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ MinIO Console stop had issues: {result.stderr}")
                
                # Stop Kibana
                result = subprocess.run(
                    ["docker", "compose", "stop", "kibana"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Kibana stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Kibana stop had issues: {result.stderr}")
                
                # Stop Flowise
                result = subprocess.run(
                    ["docker", "compose", "stop", "flowise"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Flowise stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Flowise stop had issues: {result.stderr}")
                
                # Stop n8n
                result = subprocess.run(
                    ["docker", "compose", "stop", "n8n"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ n8n stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ n8n stop had issues: {result.stderr}")
                
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Admin UI services shutdown completed!")
                
            else:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Services directory not found: {services_dir}")
                admin_state["shutdown_in_progress"] = False
                return
            
        except Exception as e:
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Admin UI shutdown failed with error: {str(e)}")
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_dir)
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Restored working directory to: {original_dir}")
            except Exception as e:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to restore working directory: {str(e)}")
            admin_state["shutdown_in_progress"] = False
    
    # Start the worker thread
    if not admin_state["shutdown_in_progress"]:
        admin_state["shutdown_thread"] = threading.Thread(target=stop_ui_worker, daemon=True)
        admin_state["shutdown_thread"].start()

def shutdown_services():
    """Stop all services in the background"""
    
    def shutdown_worker():
        admin_state["shutdown_in_progress"] = True
        admin_state["shutdown_logs"] = []
        
        # Store the original working directory
        original_dir = os.getcwd()
        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Stopping MEP AI NABOX services...")
        admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📍 Original directory: {original_dir}")
        
        try:
            # Step 1: Stop core services first (Native Host-based Processing)
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Stopping native core system services...")
            
            # Navigate to the core directory
            core_dir = os.path.dirname(original_dir)
            
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for core directory: {core_dir}")
            
            if os.path.exists(core_dir):
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found core directory")
                os.chdir(core_dir)
                
                # Stop native services using the start_native_services.sh script
                result = subprocess.run(
                    ["./start_native_services.sh", "--stop", "all"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Native core system services stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to stop native core services: {result.stderr}")
            else:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Core directory not found: {core_dir}")
            
            # Step 2: Stop infrastructure services
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 Stopping infrastructure services...")
            
            # Navigate to the services directory
            # Since we're in core/dashboard, we need to go up one level to reach the project root
            project_root = os.path.dirname(original_dir)
            services_dir = os.path.join(project_root, 'services')
            
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for services directory: {services_dir}")
            
            if os.path.exists(services_dir):
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found services directory")
                os.chdir(services_dir)
                result = subprocess.run(
                    ["docker", "compose", "down"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Infrastructure services stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to stop infrastructure services: {result.stderr}")
            else:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Services directory not found: {services_dir}")
            
            # Final status check
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Performing final status checks...")
            
            if not check_infrastructure_services():
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Infrastructure services stopped")
            else:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Some infrastructure services may still be running")
            
            if not check_core_services():
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Core services stopped")
            else:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Some core services may still be running")
            
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 MEP AI NABOX shutdown completed!")
            
        except Exception as e:
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Shutdown failed with error: {str(e)}")
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_dir)
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Restored working directory to: {original_dir}")
            except Exception as e:
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to restore working directory: {str(e)}")
            admin_state["shutdown_in_progress"] = False
    
    # Start the worker thread
    if not admin_state["shutdown_in_progress"]:
        admin_state["shutdown_thread"] = threading.Thread(target=shutdown_worker, daemon=True)
        admin_state["shutdown_thread"].start()

# Admin endpoints
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel page"""
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/api/admin/status")
async def get_admin_status():
    """Get admin status and service states"""
    return AdminStatus(
        infrastructure_running=check_infrastructure_services(),
        core_system_running=check_core_services(),
        startup_in_progress=admin_state["startup_in_progress"],
        startup_logs=admin_state["startup_logs"],
        shutdown_in_progress=admin_state["shutdown_in_progress"],
        shutdown_logs=admin_state["shutdown_logs"],
        last_update=datetime.now()
    )

@app.post("/api/admin/start-services")
async def start_all_services():
    """Start all services"""
    if admin_state["startup_in_progress"]:
        raise HTTPException(status_code=400, detail="Startup already in progress")
    
    startup_services()
    return {"message": "Service startup initiated", "status": "starting"}

@app.post("/api/admin/start-admin-ui-services")
async def start_admin_ui_services():
    """Start admin UI services"""
    if admin_state["startup_in_progress"]:
        raise HTTPException(status_code=400, detail="Startup already in progress")
    
    startup_admin_ui_services()
    return {"message": "Admin UI services startup initiated", "status": "starting"}

@app.post("/api/admin/stop-admin-ui-services")
async def stop_admin_ui_services():
    """Stop admin UI services"""
    if admin_state["shutdown_in_progress"]:
        raise HTTPException(status_code=400, detail="Shutdown already in progress")
    
    stop_admin_ui_services()
    return {"message": "Admin UI services shutdown initiated", "status": "stopping"}

@app.post("/api/admin/stop-services")
async def stop_all_services():
    """Stop all services"""
    if admin_state["shutdown_in_progress"]:
        raise HTTPException(status_code=400, detail="Shutdown already in progress")
    
    shutdown_services()
    return {"message": "Service shutdown initiated", "status": "stopping"}

@app.get("/api/admin/startup-logs")
async def get_startup_logs():
    """Get startup logs"""
    return {
        "logs": admin_state["startup_logs"],
        "in_progress": admin_state["startup_in_progress"]
    }

@app.get("/api/admin/shutdown-logs")
async def get_shutdown_logs():
    """Get shutdown logs"""
    return {
        "logs": admin_state["shutdown_logs"],
        "in_progress": admin_state["shutdown_in_progress"]
    }

@app.get("/api/admin/service-status")
async def get_service_status():
    """Get detailed status of all services"""
    
    # Core Services (Native Host-based Processing)
    core_services = [
        {"name": "API Gateway", "port": 8011, "endpoint": "/health", "description": "Unified entry point for all client interactions", "service_key": "api-gateway", "admin_url": "http://localhost:8011/docs"},
        {"name": "Core Processor", "port": 8001, "endpoint": "/docs", "description": "Main document processing orchestrator", "service_key": "core-processor", "admin_url": "http://localhost:8001/docs"},
        {"name": "Document Router", "port": 8002, "endpoint": "/health", "description": "Intelligent document routing and processing", "service_key": "document-router", "admin_url": "http://localhost:8002/docs"},
        {"name": "Processing Pipeline", "port": 8003, "endpoint": "/health", "description": "Orchestrated document processing workflow", "service_key": "processing-pipeline", "admin_url": "http://localhost:8003/docs"},
        {"name": "Storage Manager", "port": 8004, "endpoint": "/health", "description": "Unified data storage and retrieval interface", "service_key": "storage-manager", "admin_url": "http://localhost:8004/docs"},
        {"name": "Text Processor", "port": 8005, "endpoint": "/health", "description": "Text extraction and processing", "service_key": "text-processor", "admin_url": "http://localhost:8005/docs"},
        {"name": "Metadata Processor", "port": 8006, "endpoint": "/health", "description": "Metadata extraction and validation", "service_key": "metadata-processor", "admin_url": "http://localhost:8006/docs"},
        {"name": "Embedding Processor", "port": 8007, "endpoint": "/health", "description": "Vector embedding generation using Ollama", "service_key": "embedding-processor", "admin_url": "http://localhost:8007/docs"},
        {"name": "Entity Processor", "port": 8008, "endpoint": "/health", "description": "Entity extraction and relationship mapping", "service_key": "entity-processor", "admin_url": "http://localhost:8008/docs"},
        {"name": "File Watcher", "port": 8009, "endpoint": "/health", "description": "Monitor local folders for new documents", "service_key": "file-watcher", "admin_url": "http://localhost:8009/docs"},
        {"name": "Queue Worker", "port": None, "endpoint": "/queue-worker/health", "description": "Background job processor for guaranteed document processing", "service_key": "queue-worker", "admin_url": "http://localhost:8003/docs"},
        {"name": "Status Worker", "port": None, "endpoint": "/status-worker/health", "description": "Background status update processor for reliable status synchronization", "service_key": "status-worker", "admin_url": "http://localhost:8003/docs"},
        {"name": "Ollama", "port": 11434, "endpoint": "/api/tags", "description": "Self-hosted LLM and embedding service", "service_key": "ollama", "admin_url": "http://localhost:11434/api/tags"}
    ]
    
    # Infrastructure Services (from services docker-compose)
    infrastructure_services = [
        {"name": "PostgreSQL", "port": 5432, "endpoint": None, "description": "Primary database", "service_key": "postgres", "admin_url": "http://localhost:8080"},
        {"name": "Elasticsearch", "port": 9200, "endpoint": "/_cluster/health", "description": "Search and analytics engine", "service_key": "elasticsearch", "admin_url": "http://localhost:5601"},
        {"name": "Qdrant", "port": 6333, "endpoint": "/collections", "description": "Vector database", "api_key": "qdrant_api_key", "service_key": "qdrant", "admin_url": f"http://localhost:7070/index.html?api_token={QDRANT_API_KEY}"},
        {"name": "Redis", "port": 6379, "endpoint": None, "description": "In-memory data structure store", "service_key": "redis", "admin_url": "http://localhost:8081"},
        {"name": "MinIO", "port": 9000, "endpoint": "/minio/health/live", "description": "Object storage", "service_key": "minio", "admin_url": "http://localhost:9001"},
        {"name": "Neo4j", "port": 7474, "endpoint": "/", "description": "Graph database", "service_key": "neo4j", "admin_url": "http://localhost:7474"},
        {"name": "Kibana", "port": 5601, "endpoint": "/", "description": "Elasticsearch management and visualization", "service_key": "kibana", "admin_url": "http://localhost:5601"},
        {"name": "Flowise", "port": 3001, "endpoint": "/", "description": "LLM Flow Builder", "service_key": "flowise", "admin_url": "http://localhost:3001"},
        {"name": "n8n", "port": 5678, "endpoint": "/", "description": "Workflow automation platform", "service_key": "n8n", "admin_url": "http://localhost:5678"}
    ]
    
    # Admin UI Services (including pgAdmin and Redis Commander)
    admin_ui_services = [
        {"name": "Prometheus", "port": 9090, "endpoint": "/-/healthy", "description": "Metrics collection and monitoring", "service_key": "prometheus", "admin_url": "http://localhost:9090"},
        {"name": "Grafana", "port": 3002, "endpoint": "/api/health", "description": "Monitoring dashboards", "service_key": "grafana", "admin_url": "http://localhost:3002"},
        {"name": "Qdrant UI", "port": 7070, "endpoint": "/index.html", "description": "Vector database management interface", "service_key": "qdrantui", "admin_url": f"http://localhost:7070/index.html?api_token={QDRANT_API_KEY}"},
        {"name": "pgAdmin", "port": 8080, "endpoint": "/", "description": "PostgreSQL administration", "service_key": "pgadmin", "admin_url": "http://localhost:8080"},
        {"name": "Redis Commander", "port": 8081, "endpoint": "/", "description": "Redis management interface", "service_key": "redis-commander", "admin_url": "http://localhost:8081"}
    ]
    
    def check_native_service_process(service_name: str) -> bool:
        """Check if a native service process is running"""
        try:
            import subprocess
            # Check for Python processes running the service
            result = subprocess.run(
                ["pgrep", "-f", f"python.*{service_name}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def check_service_status(service):
        """Check if a service is running"""
        try:
            # For services without ports (like queue/status workers), check via HTTP endpoint
            if service["port"] is None:
                if service["endpoint"]:
                    try:
                        import httpx
                        with httpx.Client(timeout=3.0) as client:
                            # Add API key header if service requires it
                            headers = {}
                            if "api_key" in service:
                                headers["api-key"] = service["api_key"]
                            
                            # Use processing pipeline port for queue/status workers
                            response = client.get(f"http://localhost:8003{service['endpoint']}", headers=headers)
                            return "running" if response.status_code in [200, 302, 404] else "unhealthy"
                    except:
                        return "unknown"
                else:
                    return "unknown"
            
            # For services with ports, check port and HTTP endpoint
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", service["port"]))
            sock.close()
            
            if result == 0:
                # Port is open, try HTTP check if endpoint is specified
                if service["endpoint"]:
                    try:
                        import httpx
                        with httpx.Client(timeout=3.0) as client:
                            # Add API key header if service requires it
                            headers = {}
                            if "api_key" in service:
                                headers["api-key"] = service["api_key"]
                            
                            response = client.get(f"http://localhost:{service['port']}{service['endpoint']}", headers=headers)
                            return "running" if response.status_code in [200, 302, 404] else "unhealthy"
                    except:
                        return "running"  # Port open but HTTP failed, assume running
                else:
                    return "running"
            else:
                # For native services, also check if the process is running
                if service["service_key"] in ["api-gateway", "core-processor", "document-router", "processing-pipeline", 
                                            "storage-manager", "text-processor", "metadata-processor", "embedding-processor", 
                                            "entity-processor", "file-watcher"]:
                    if check_native_service_process(service["service_key"]):
                        return "running"  # Process is running but port might not be ready yet
                return "stopped"
        except:
            return "unknown"
    
    # Check status for all services
    core_services_with_status = []
    for service in core_services:
        status = check_service_status(service)
        core_services_with_status.append({
            **service,
            "status": status,
            "category": "core"
        })
    
    infrastructure_services_with_status = []
    for service in infrastructure_services:
        status = check_service_status(service)
        infrastructure_services_with_status.append({
            **service,
            "status": status,
            "category": "infrastructure"
        })
    
    admin_ui_services_with_status = []
    for service in admin_ui_services:
        status = check_service_status(service)
        admin_ui_services_with_status.append({
            **service,
            "status": status,
            "category": "admin_ui"
        })
    
    return {
        "core_services": core_services_with_status,
        "infrastructure_services": infrastructure_services_with_status,
        "admin_ui_services": admin_ui_services_with_status,
        "last_update": datetime.now()
    }

@app.post("/api/admin/service/{service_key}/start")
async def start_individual_service(service_key: str):
    """Start an individual service"""
    try:
        import subprocess
        import os
        
        # Store original directory
        original_dir = os.getcwd()
        
        try:
            # Handle native core services
            if service_key in ["api-gateway", "core-processor", "document-router", "processing-pipeline", "storage-manager", "text-processor", "metadata-processor", "embedding-processor", "entity-processor", "file-watcher", "queue-worker", "status-worker"]:
                # Native core service - use start_native_services.sh
                os.chdir("/home/lie/repo_mep/mep_ainabox/core")
                cmd = ["./start_native_services.sh", "--start", service_key]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Native service {service_key} started successfully", "status": "started"}
                else:
                    return {"message": f"Failed to start native service {service_key}: {result.stderr}", "status": "failed"}
            
            # Handle infrastructure services (still use Docker)
            elif service_key in ["postgres", "elasticsearch", "qdrant", "redis", "minio", "neo4j", "kibana", "flowise", "n8n"]:
                # Infrastructure service - use services docker-compose
                compose_file = "services/docker-compose.yml"
                service_name = service_key
                os.chdir("/home/lie/repo_mep/mep_ainabox")
                
                cmd = ["docker", "compose", "-f", compose_file, "up", "-d", service_name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Infrastructure service {service_key} started successfully", "status": "started"}
                else:
                    return {"message": f"Failed to start infrastructure service {service_key}: {result.stderr}", "status": "failed"}
            
            # Handle admin UI services (still use Docker)
            elif service_key in ["prometheus", "grafana", "qdrantui", "pgadmin", "redis-commander"]:
                # Admin UI service - use services docker-compose with profile
                compose_file = "services/docker-compose.yml"
                service_name = service_key
                os.chdir("/home/lie/repo_mep/mep_ainabox")
                
                if service_key in ["prometheus", "grafana"]:
                    cmd = ["docker", "compose", "-f", compose_file, "--profile", service_key, "up", "-d", service_name]
                else:
                    cmd = ["docker", "compose", "-f", compose_file, "up", "-d", service_name]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Admin UI service {service_key} started successfully", "status": "started"}
                else:
                    return {"message": f"Failed to start admin UI service {service_key}: {result.stderr}", "status": "failed"}
            else:
                raise HTTPException(status_code=404, detail=f"Service {service_key} not found")
                
        finally:
            # Restore original directory
            os.chdir(original_dir)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting service {service_key}: {str(e)}")

@app.post("/api/admin/service/{service_key}/stop")
async def stop_individual_service(service_key: str):
    """Stop an individual service"""
    try:
        import subprocess
        import os
        
        # Store original directory
        original_dir = os.getcwd()
        
        try:
            # Handle native core services
            if service_key in ["api-gateway", "core-processor", "document-router", "processing-pipeline", "storage-manager", "text-processor", "metadata-processor", "embedding-processor", "entity-processor", "file-watcher", "queue-worker", "status-worker"]:
                # Native core service - use start_native_services.sh
                os.chdir("/home/lie/repo_mep/mep_ainabox/core")
                cmd = ["./start_native_services.sh", "--stop", service_key]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Native service {service_key} stopped successfully", "status": "stopped"}
                else:
                    return {"message": f"Failed to stop native service {service_key}: {result.stderr}", "status": "failed"}
            
            # Handle infrastructure services (still use Docker)
            elif service_key in ["postgres", "elasticsearch", "qdrant", "redis", "minio", "neo4j", "kibana", "flowise", "n8n"]:
                # Infrastructure service - use services docker-compose
                compose_file = "services/docker-compose.yml"
                service_name = service_key
                os.chdir("/home/lie/repo_mep/mep_ainabox")
                
                cmd = ["docker", "compose", "-f", compose_file, "stop", service_name]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Infrastructure service {service_key} stopped successfully", "status": "stopped"}
                else:
                    return {"message": f"Failed to stop infrastructure service {service_key}: {result.stderr}", "status": "failed"}
            
            # Handle admin UI services (still use Docker)
            elif service_key in ["prometheus", "grafana", "qdrantui", "pgadmin", "redis-commander"]:
                # Admin UI service - use services docker-compose with profile
                compose_file = "services/docker-compose.yml"
                service_name = service_key
                os.chdir("/home/lie/repo_mep/mep_ainabox")
                
                if service_key in ["prometheus", "grafana"]:
                    cmd = ["docker", "compose", "-f", compose_file, "--profile", service_key, "stop", service_name]
                else:
                    cmd = ["docker", "compose", "-f", compose_file, "stop", service_name]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return {"message": f"Admin UI service {service_key} stopped successfully", "status": "stopped"}
                else:
                    return {"message": f"Failed to stop admin UI service {service_key}: {result.stderr}", "status": "failed"}
            else:
                raise HTTPException(status_code=404, detail=f"Service {service_key} not found")
                
        finally:
            # Restore original directory
            os.chdir(original_dir)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping service {service_key}: {str(e)}")

# Scan Folder API Endpoints
@app.get("/scan-folder", response_class=HTMLResponse)
async def scan_folder_page(request: Request):
    """Scan folder page"""
    return templates.TemplateResponse("scan_folder.html", {"request": request})

@app.get("/folder-browser", response_class=HTMLResponse)
async def folder_browser_page(request: Request):
    """Dynamic folder browser page for selecting folders to scan"""
    return templates.TemplateResponse("folder_browser.html", {"request": request})

@app.post("/api/scan-folder/start")
async def start_scan_folder(request: ScanFolderRequest):
    """Start a new scan folder execution"""
    try:
        logger.info(f"Starting scan folder execution for: {request.folder_path}")
        
        # Validate folder path
        if not os.path.exists(request.folder_path):
            error_msg = f"Folder does not exist: {request.folder_path}"
            logger.warning(f"Scan folder validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        if not os.path.isdir(request.folder_path):
            error_msg = f"Path is not a directory: {request.folder_path}"
            logger.warning(f"Scan folder validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Check if folder is readable
        if not os.access(request.folder_path, os.R_OK):
            error_msg = f"Folder is not readable: {request.folder_path}"
            logger.warning(f"Scan folder validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info(f"Folder validation passed for: {request.folder_path}")
        
        # Create execution
        execution_id = str(uuid.uuid4())
        execution = ScanExecution(
            id=execution_id,
            folder_path=request.folder_path,
            processing_mode=request.processing_mode,
            concurrent_limit=request.concurrent_limit,
            max_depth=request.max_depth,
            recursive=request.recursive,
            save_report=request.save_report,
            status="pending",
            started_at=datetime.now()
        )
        
        scan_executions[execution_id] = execution
        logger.info(f"Created scan execution {execution_id} for folder: {request.folder_path}")
        
        # Start background worker with async wrapper
        def run_async_worker():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(scan_folder_worker(execution_id, request))
            finally:
                loop.close()
        
        worker_thread = threading.Thread(
            target=run_async_worker,
            daemon=True
        )
        worker_thread.start()
        
        logger.info(f"Started background worker for execution {execution_id}")
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "message": f"Scan execution started for folder: {request.folder_path}"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = f"Unexpected error starting scan folder: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/scan-folder/executions")
async def get_scan_executions():
    """Get all scan executions"""
    executions = []
    for execution in scan_executions.values():
        # Convert to dict
        execution_dict = execution.dict()
        executions.append(execution_dict)
    
    # Sort by started_at (newest first)
    executions.sort(key=lambda x: x['started_at'], reverse=True)
    return executions

@app.get("/api/scan-folder/executions/{execution_id}")
async def get_scan_execution(execution_id: str):
    """Get a specific scan execution"""
    if execution_id not in scan_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = scan_executions[execution_id]
    execution_dict = execution.dict()
    return execution_dict

@app.post("/api/scan-folder/executions/{execution_id}/stop")
async def stop_scan_execution_api(execution_id: str):
    """Stop a running scan execution"""
    if execution_id not in scan_executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    success = stop_scan_execution(execution_id)
    if success:
        return {"message": "Execution stopped successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to stop execution")

@app.post("/api/scan-folder/executions/clear-completed")
async def clear_completed_executions_api():
    """Clear completed, failed, and stopped executions"""
    count = clear_completed_executions()
    return {"message": f"Cleared {count} completed executions"}

class FolderPreviewRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    max_depth: Optional[int] = None

class FileItem(BaseModel):
    name: str
    type: str  # file or directory
    size: Optional[int] = None
    supported: Optional[bool] = None
    children: Optional[List['FileItem']] = None

class FolderPreviewResponse(BaseModel):
    folder_path: str
    total_files: int
    supported_files: int
    unsupported_files: int
    directories: int
    total_size: int
    recursive: bool
    max_depth: Optional[int]
    file_structure: List[FileItem]

@app.post("/api/scan-folder/preview")
async def preview_folder(request: FolderPreviewRequest):
    """Preview folder structure without processing files"""
    try:
        # Validate folder path
        if not request.folder_path:
            raise HTTPException(status_code=400, detail="Folder path is required")
        
        if not os.path.exists(request.folder_path):
            raise HTTPException(status_code=400, detail=f"Folder does not exist: {request.folder_path}")
        
        if not os.path.isdir(request.folder_path):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.folder_path}")
        
        if not os.access(request.folder_path, os.R_OK):
            raise HTTPException(status_code=400, detail=f"Folder is not readable: {request.folder_path}")
        
        logger.info(f"Starting folder preview for: {request.folder_path}")
        
        # Scan folder structure
        total_files = 0
        supported_files = 0
        unsupported_files = 0
        directories = 0
        total_size = 0
        file_structure = []
        
        # Supported file extensions (same as folder scanner)
        SUPPORTED_EXTENSIONS = {
            '.pdf', '.docx', '.doc', '.txt', '.html', '.htm', 
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff',
            '.csv', '.xlsx', '.xls'
        }
        
        def scan_directory(path: str, depth: int = 0) -> List[FileItem]:
            nonlocal total_files, supported_files, unsupported_files, directories, total_size
            
            items = []
            
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    
                    if os.path.isdir(item_path):
                        directories += 1
                        children = []
                        
                        if request.recursive and (request.max_depth is None or depth < request.max_depth):
                            children = scan_directory(item_path, depth + 1)
                        
                        items.append(FileItem(
                            name=item,
                            type="directory",
                            children=children
                        ))
                    else:
                        total_files += 1
                        file_size = os.path.getsize(item_path)
                        total_size += file_size
                        
                        # Check if file is supported
                        file_ext = os.path.splitext(item)[1].lower()
                        is_supported = file_ext in SUPPORTED_EXTENSIONS
                        
                        if is_supported:
                            supported_files += 1
                        else:
                            unsupported_files += 1
                        
                        items.append(FileItem(
                            name=item,
                            type="file",
                            size=file_size,
                            supported=is_supported
                        ))
            except PermissionError:
                logger.warning(f"Permission denied accessing: {path}")
            except Exception as e:
                logger.error(f"Error scanning directory {path}: {e}")
            
            return items
        
        # Start scanning
        file_structure = scan_directory(request.folder_path)
        
        # Sort items (directories first, then files alphabetically)
        def sort_items(items: List[FileItem]) -> List[FileItem]:
            for item in items:
                if item.children:
                    item.children = sort_items(item.children)
            return sorted(items, key=lambda x: (x.type != "directory", x.name.lower()))
        
        file_structure = sort_items(file_structure)
        
        logger.info(f"Folder preview completed for {request.folder_path}: {total_files} files, {directories} directories")
        
        return FolderPreviewResponse(
            folder_path=request.folder_path,
            total_files=total_files,
            supported_files=supported_files,
            unsupported_files=unsupported_files,
            directories=directories,
            total_size=total_size,
            recursive=request.recursive,
            max_depth=request.max_depth,
            file_structure=file_structure
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error previewing folder: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

DEESEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key")
DEESEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

@app.post("/api/llm-search")
async def llm_search(request: Request):
    data = await request.json()
    query = data.get("query", "")
    if not query:
        return {"results": [], "llm_response": "No query provided."}

    # 1. Generate embedding for the query (reuse embedding_processor logic)
    # 2. Search Qdrant for similar vectors
    # 3. Send top results as context to DeepSeek API
    # 4. Return results
    try:
        # --- Step 1: Generate embedding using HuggingFace (or your embedding provider) ---
        # Call the embedding_processor API to get the embedding
        embedding_resp = await httpx.AsyncClient().post(
            f"http://localhost:8007/embed?text={query}&provider=huggingface"
        )
        embedding_data = embedding_resp.json()
        embedding = embedding_data.get("embedding")
        if not embedding:
            return {"results": [], "llm_response": "Failed to generate embedding."}

        # --- Step 2: Search Qdrant ---
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "qdrant_api_key")
        search_payload = {
            "vector": embedding,
            "top": 5,
            "with_payload": True
        }
        qdrant_resp = await httpx.AsyncClient().post(
            f"{qdrant_url}/collections/documents/points/search",
            headers={"api-key": qdrant_api_key, "Content-Type": "application/json"},
            json=search_payload
        )
        qdrant_results = qdrant_resp.json().get("result", [])
        # Get Qdrant database statistics
        try:
            qdrant_stats_resp = await httpx.AsyncClient().get(
                f"{qdrant_url}/collections/documents",
                headers={"api-key": qdrant_api_key, "Content-Type": "application/json"},
                timeout=10.0
            )
            qdrant_stats = qdrant_stats_resp.json()
            collection_info = qdrant_stats.get("result", {})
            total_points = collection_info.get("points_count", 0)
            total_vectors = collection_info.get("vectors_count", 0)
        except:
            total_points = len(qdrant_results)
            total_vectors = len(qdrant_results)

        # Prepare enhanced context for LLM
        context_texts = [r["payload"].get("text", "") for r in qdrant_results]
        context = "\n---\n".join(context_texts)
        
        # Add database metadata to context
        db_metadata = f"""
DATABASE INFORMATION:
- Total documents in vector database: {total_points}
- Total vector embeddings: {total_vectors}
- Search results found: {len(qdrant_results)}

DOCUMENT CONTENT:
{context}
"""
        # --- Step 3: Call DeepSeek API ---
        if DEESEEK_API_KEY == "your-deepseek-api-key":
            llm_answer = "DeepSeek API key not configured. Please set the DEEPSEEK_API_KEY environment variable."
        else:
            # Debug: Print the API key (first 10 characters) and URL
            print(f"Using DeepSeek API key: {DEESEEK_API_KEY[:10]}...")
            print(f"Using DeepSeek API URL: {DEESEEK_API_URL}")
            deepseek_payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": """You are a helpful assistant with access to a vector database containing document embeddings. 

You can:
1. Answer questions about the documents in the database
2. Provide statistics about the database (number of documents, types, etc.)
3. Analyze the content and patterns in the documents
4. Help users understand what information is available

When asked about database statistics, provide accurate information from the database metadata provided.
When asked about document content, use the provided document excerpts to answer.
Always be helpful and informative."""},
                    {"role": "user", "content": f"Database Information and Document Content:\n{db_metadata}\n\nUser Query: {query}"}
                ],
                "stream": False
            }
            deepseek_headers = {
                "Authorization": f"Bearer {DEESEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            try:
                print(f"Sending request to DeepSeek API...")
                llm_resp = await httpx.AsyncClient().post(
                    DEESEEK_API_URL,
                    headers=deepseek_headers,
                    json=deepseek_payload,
                    timeout=60.0  # Increase timeout to 60 seconds
                )
                print(f"DeepSeek API response status: {llm_resp.status_code}")
                llm_resp.raise_for_status()  # This will raise an exception for HTTP errors
                llm_data = llm_resp.json()
                print(f"DeepSeek API response: {llm_data}")
                llm_answer = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "No answer.")
                print(f"Extracted answer: {llm_answer}")
            except httpx.HTTPStatusError as e:
                error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                print(f"HTTP Error: {error_detail}")
                llm_answer = f"Error calling DeepSeek API: {error_detail}"
            except Exception as e:
                print(f"Exception: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                llm_answer = f"Error calling DeepSeek API: {str(e)}"
        # --- Step 4: Return results ---
        results = [
            {
                "score": r.get("score"),
                "text": r["payload"].get("text", ""),
                "metadata": r["payload"].get("metadata", {})
            }
            for r in qdrant_results
        ]
        return {"results": results, "llm_response": llm_answer}
    except Exception as e:
        return {"results": [], "llm_response": f"Error: {str(e)}"}

@app.get("/llm-search", response_class=HTMLResponse)
async def llm_search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.post("/api/db-query")
async def database_query(request: Request):
    """Direct database query endpoint for asking about the vector database"""
    data = await request.json()
    query = data.get("query", "")
    if not query:
        return {"answer": "No query provided."}

    try:
        # Get Qdrant database statistics
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "qdrant_api_key")
        
        # Get collection statistics
        qdrant_stats_resp = await httpx.AsyncClient().get(
            f"{qdrant_url}/collections/documents",
            headers={"api-key": qdrant_api_key, "Content-Type": "application/json"},
            timeout=10.0
        )
        qdrant_stats = qdrant_stats_resp.json()
        collection_info = qdrant_stats.get("result", {})
        total_points = collection_info.get("points_count", 0)
        total_vectors = collection_info.get("vectors_count", 0)
        
        # Get sample documents for context
        sample_resp = await httpx.AsyncClient().post(
            f"{qdrant_url}/collections/documents/points/scroll",
            headers={"api-key": qdrant_api_key, "Content-Type": "application/json"},
            json={"limit": 10, "with_payload": True},
            timeout=10.0
        )
        sample_data = sample_resp.json()
        sample_docs = sample_data.get("result", {}).get("points", [])
        
        # Prepare context
        sample_texts = [doc["payload"].get("text", "")[:200] for doc in sample_docs]
        sample_context = "\n---\n".join(sample_texts)
        
        # Create database context
        db_context = f"""
VECTOR DATABASE INFORMATION:
- Total documents: {total_points}
- Total vector embeddings: {total_vectors}
- Collection name: documents

SAMPLE DOCUMENTS (first 10):
{sample_context}

USER QUERY: {query}
"""
        
        # Call DeepSeek API
        if DEESEEK_API_KEY == "your-deepseek-api-key":
            answer = "DeepSeek API key not configured."
        else:
            deepseek_payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": """You are a database assistant with access to a vector database. 
Answer questions about the database content, statistics, and documents. Be informative and helpful."""},
                    {"role": "user", "content": db_context}
                ],
                "stream": False
            }
            deepseek_headers = {
                "Authorization": f"Bearer {DEESEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            llm_resp = await httpx.AsyncClient().post(
                DEESEEK_API_URL,
                headers=deepseek_headers,
                json=deepseek_payload,
                timeout=60.0
            )
            llm_resp.raise_for_status()
            llm_data = llm_resp.json()
            answer = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "No answer.")
        
        return {
            "answer": answer,
            "database_stats": {
                "total_documents": total_points,
                "total_vectors": total_vectors,
                "sample_documents": len(sample_docs)
            }
        }
        
    except Exception as e:
        return {"answer": f"Error querying database: {str(e)}"}

# Dynamic folder selection and browsing endpoints
class FolderBrowseRequest(BaseModel):
    path: str = "/"
    show_hidden: bool = False

class FolderBrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    folders: List[Dict[str, Any]]
    files: List[Dict[str, Any]]
    error: Optional[str] = None

@app.post("/api/folder/browse")
async def browse_folder(request: FolderBrowseRequest):
    """Browse folders for dynamic selection"""
    try:
        import os
        from pathlib import Path
        
        # Resolve the path
        path = Path(request.path).resolve()
        
        # Security check - ensure path is accessible
        if not path.exists():
            return FolderBrowseResponse(
                current_path=str(path),
                error="Path does not exist"
            )
        
        if not path.is_dir():
            return FolderBrowseResponse(
                current_path=str(path),
                error="Path is not a directory"
            )
        
        # Get parent path
        parent_path = str(path.parent) if path.parent != path else None
        
        # List contents
        folders = []
        files = []
        
        try:
            for item in path.iterdir():
                # Skip hidden files unless requested
                if not request.show_hidden and item.name.startswith('.'):
                    continue
                
                try:
                    stat = item.stat()
                    item_info = {
                        "name": item.name,
                        "path": str(item),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "is_dir": item.is_dir(),
                        "is_file": item.is_file(),
                        "is_symlink": item.is_symlink()
                    }
                    
                    if item.is_dir():
                        folders.append(item_info)
                    else:
                        files.append(item_info)
                        
                except (PermissionError, OSError):
                    # Skip items we can't access
                    continue
            
            # Sort folders and files
            folders.sort(key=lambda x: x["name"].lower())
            files.sort(key=lambda x: x["name"].lower())
            
            return FolderBrowseResponse(
                current_path=str(path),
                parent_path=parent_path,
                folders=folders,
                files=files
            )
            
        except PermissionError:
            return FolderBrowseResponse(
                current_path=str(path),
                error="Permission denied"
            )
            
    except Exception as e:
        return FolderBrowseResponse(
            current_path=request.path,
            error=f"Error browsing folder: {str(e)}"
        )

class FolderMountRequest(BaseModel):
    folder_path: str
    folder_name: Optional[str] = None

class FolderMountResponse(BaseModel):
    success: bool
    unique_folder_name: Optional[str] = None
    error_message: Optional[str] = None

@app.post("/api/folder/mount")
async def mount_folder(request: FolderMountRequest):
    """Mount a folder using the volume manager"""
    try:
        import httpx
        
        # Validate the folder path
        import os
        from pathlib import Path
        
        folder_path = Path(request.folder_path).resolve()
        
        if not folder_path.exists():
            return FolderMountResponse(
                success=False,
                error_message="Folder does not exist"
            )
        
        if not folder_path.is_dir():
            return FolderMountResponse(
                success=False,
                error_message="Path is not a directory"
            )
        
        # Call the volume manager
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HOST_VOLUME_MANAGER_URL}/mount",
                json={
                    "host_path": str(folder_path),
                    "folder_name": request.folder_name
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return FolderMountResponse(
                    success=False,
                    error_message=f"Volume manager error: {response.text}"
                )
            
            result = response.json()
            if result.get("success"):
                return FolderMountResponse(
                    success=True,
                    unique_folder_name=result.get("unique_folder_name")
                )
            else:
                return FolderMountResponse(
                    success=False,
                    error_message=result.get("error_message", "Unknown error")
                )
                
    except Exception as e:
        return FolderMountResponse(
            success=False,
            error_message=f"Error mounting folder: {str(e)}"
        )

class FolderUnmountRequest(BaseModel):
    folder_name: str

class FolderUnmountResponse(BaseModel):
    success: bool
    error_message: Optional[str] = None

@app.post("/api/folder/unmount")
async def unmount_folder(request: FolderUnmountRequest):
    """Unmount a folder using the volume manager"""
    try:
        import httpx
        
        # Call the volume manager
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HOST_VOLUME_MANAGER_URL}/unmount",
                json={
                    "folder_name": request.folder_name
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return FolderUnmountResponse(
                    success=False,
                    error_message=f"Volume manager error: {response.text}"
                )
            
            result = response.json()
            if result.get("success"):
                return FolderUnmountResponse(success=True)
            else:
                return FolderUnmountResponse(
                    success=False,
                    error_message=result.get("error_message", "Unknown error")
                )
                
    except Exception as e:
        return FolderUnmountResponse(
            success=False,
            error_message=f"Error unmounting folder: {str(e)}"
        )

class FolderListResponse(BaseModel):
    folders: List[str]
    error_message: Optional[str] = None

@app.get("/api/folder/list")
async def list_mounted_folders():
    """List all mounted folders"""
    try:
        import httpx
        
        # Call the volume manager
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HOST_VOLUME_MANAGER_URL}/list",
                timeout=10.0
            )
            
            if response.status_code != 200:
                return FolderListResponse(
                    folders=[],
                    error_message=f"Volume manager error: {response.text}"
                )
            
            result = response.json()
            return FolderListResponse(
                folders=result.get("folders", [])
            )
                
    except Exception as e:
        return FolderListResponse(
            folders=[],
            error_message=f"Error listing folders: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info") 