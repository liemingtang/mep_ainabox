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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
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
        "port": 8011,
        "url": "http://localhost:8011",
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
    "storage-manager": f"{STORAGE_MANAGER_URL}/health",
    "text-processor": "http://localhost:8005/health",
    "metadata-processor": "http://localhost:8006/health",
    "embedding-processor": "http://localhost:8007/health",
    "entity-processor": "http://localhost:8008/health",
    "processing-pipeline": "http://localhost:8003/health",
    "document-router": "http://localhost:8002/health",
    "api-gateway": "http://localhost:8011/health",
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
if current_dir.endswith('/dashboard'):
    # Running from dashboard directory
    static_dir = "static"
    templates_dir = "templates"
else:
    # Running from core directory
    static_dir = "dashboard/static"
    templates_dir = "dashboard/templates"

print(f"Static directory: {static_dir}")
print(f"Templates directory: {templates_dir}")

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

# Global admin state
admin_state = {
    "startup_in_progress": False,
    "startup_logs": [],
    "startup_thread": None,
    "shutdown_in_progress": False,
    "shutdown_logs": [],
    "shutdown_thread": None
}

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
        
        service_detail = ServiceDetail(
            name=service_info.get("name", service_name),
            status=health.status,
            url=service_info.get("url", ""),
            port=service_info.get("port", 0),
            description=service_info.get("description", ""),
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
    """Check if core services are running"""
    try:
        # Check key core services
        services_to_check = [
            ("api-gateway", 8000),
            ("core-processor", 8001),
            ("file-watcher", 8009)
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
            
            # Step 2: Start core services
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Starting core system services...")
            
            # Navigate to the core directory (where the current docker-compose.yml is)
            # Since the dashboard is now running on the host, we need to go up one level from core/dashboard
            core_dir = os.path.dirname(original_dir)
            
            admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for core directory: {core_dir}")
            
            if os.path.exists(core_dir):
                admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found core directory")
                os.chdir(core_dir)
                result = subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Core system services started successfully")
                else:
                    admin_state["startup_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to start core services: {result.stderr}")
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
            # Step 1: Stop core services first
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Stopping core system services...")
            
            # Navigate to the core directory
            core_dir = os.path.dirname(original_dir)
            
            admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Looking for core directory: {core_dir}")
            
            if os.path.exists(core_dir):
                admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Found core directory")
                os.chdir(core_dir)
                result = subprocess.run(
                    ["docker", "compose", "down"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Core system services stopped successfully")
                else:
                    admin_state["shutdown_logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to stop core services: {result.stderr}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info") 