"""
Database initialization and connection management
"""

import asyncio
from typing import Dict, Any

import asyncpg
from elasticsearch import AsyncElasticsearch
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
import redis.asyncio as redis
from minio import Minio

from app.config import settings
from app.logging import get_logger

logger = get_logger("database")

# Global database connections
postgres_pool: asyncpg.Pool = None
elasticsearch_client: AsyncElasticsearch = None
qdrant_client: AsyncQdrantClient = None
neo4j_driver: AsyncGraphDatabase = None
redis_client: redis.Redis = None
minio_client: Minio = None


async def init_database():
    """Initialize all database connections"""
    logger.info("Initializing database connections...")
    
    try:
        # Initialize PostgreSQL
        await init_postgresql()
        
        # Initialize Elasticsearch
        await init_elasticsearch()
        
        # Initialize Qdrant
        await init_qdrant()
        
        # Initialize Neo4j
        await init_neo4j()
        
        # Initialize Redis
        await init_redis()
        
        # Initialize MinIO
        await init_minio()
        
        logger.info("All database connections initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise


async def init_postgresql():
    """Initialize PostgreSQL connection pool"""
    global postgres_pool
    
    try:
        postgres_config = settings.core.storage.postgresql
        
        postgres_pool = await asyncpg.create_pool(
            host=postgres_config.host,
            port=postgres_config.port,
            database=postgres_config.database,
            user=postgres_config.user,
            password=postgres_config.password,
            min_size=5,
            max_size=postgres_config.pool_size,
            command_timeout=60
        )
        
        # Test connection
        async with postgres_pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        logger.info("PostgreSQL connection pool initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        raise


async def init_elasticsearch():
    """Initialize Elasticsearch client"""
    global elasticsearch_client
    
    try:
        es_config = settings.core.storage.elasticsearch
        
        elasticsearch_client = AsyncElasticsearch(
            hosts=[{
                'host': es_config.host,
                'port': es_config.port,
                'scheme': 'http'
            }],
            basic_auth=(es_config.username, es_config.password),
            timeout=es_config.timeout,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Test connection
        await elasticsearch_client.ping()
        
        logger.info("Elasticsearch client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")
        raise


async def init_qdrant():
    """Initialize Qdrant client"""
    global qdrant_client
    
    try:
        qdrant_config = settings.core.storage.qdrant
        
        qdrant_client = AsyncQdrantClient(
            host=qdrant_config.host,
            port=qdrant_config.port,
            api_key=qdrant_config.api_key,
            timeout=qdrant_config.timeout,
            https=False
        )
        
        # Test connection
        await qdrant_client.get_collections()
        
        logger.info("Qdrant client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        raise


async def init_neo4j():
    """Initialize Neo4j driver"""
    global neo4j_driver
    
    try:
        neo4j_config = settings.core.storage.neo4j
        
        neo4j_driver = AsyncGraphDatabase.driver(
            neo4j_config.uri,
            auth=(neo4j_config.user, neo4j_config.password),
            max_connection_lifetime=3600,
            max_connection_pool_size=neo4j_config.max_connections
        )
        
        # Test connection
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
        
        logger.info("Neo4j driver initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j: {e}")
        raise


async def init_redis():
    """Initialize Redis client"""
    global redis_client
    
    try:
        redis_config = settings.core.storage.redis
        
        redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            password=redis_config.password,
            db=redis_config.db,
            max_connections=redis_config.max_connections,
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        
        logger.info("Redis client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise


async def init_minio():
    """Initialize MinIO client"""
    global minio_client
    
    try:
        minio_config = settings.core.storage.minio
        
        minio_client = Minio(
            endpoint=minio_config.endpoint,
            access_key=minio_config.access_key,
            secret_key=minio_config.secret_key,
            secure=minio_config.use_ssl
        )
        
        # Test connection and ensure bucket exists
        if not minio_client.bucket_exists(minio_config.bucket_name):
            minio_client.make_bucket(minio_config.bucket_name)
        
        logger.info("MinIO client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MinIO: {e}")
        raise


async def close_database():
    """Close all database connections"""
    logger.info("Closing database connections...")
    
    try:
        # Close PostgreSQL pool
        if postgres_pool:
            await postgres_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        # Close Elasticsearch client
        if elasticsearch_client:
            await elasticsearch_client.close()
            logger.info("Elasticsearch client closed")
        
        # Close Qdrant client
        if qdrant_client:
            await qdrant_client.close()
            logger.info("Qdrant client closed")
        
        # Close Neo4j driver
        if neo4j_driver:
            await neo4j_driver.close()
            logger.info("Neo4j driver closed")
        
        # Close Redis client
        if redis_client:
            await redis_client.close()
            logger.info("Redis client closed")
        
        logger.info("All database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


def get_postgres_pool() -> asyncpg.Pool:
    """Get PostgreSQL connection pool"""
    if not postgres_pool:
        raise RuntimeError("PostgreSQL pool not initialized")
    return postgres_pool


def get_elasticsearch_client() -> AsyncElasticsearch:
    """Get Elasticsearch client"""
    if not elasticsearch_client:
        raise RuntimeError("Elasticsearch client not initialized")
    return elasticsearch_client


def get_qdrant_client() -> AsyncQdrantClient:
    """Get Qdrant client"""
    if not qdrant_client:
        raise RuntimeError("Qdrant client not initialized")
    return qdrant_client


def get_neo4j_driver() -> AsyncGraphDatabase:
    """Get Neo4j driver"""
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")
    return neo4j_driver


def get_redis_client() -> redis.Redis:
    """Get Redis client"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client


def get_minio_client() -> Minio:
    """Get MinIO client"""
    if not minio_client:
        raise RuntimeError("MinIO client not initialized")
    return minio_client


async def health_check() -> Dict[str, Any]:
    """Perform health check on all database connections"""
    health_status = {}
    
    try:
        # PostgreSQL health check
        async with get_postgres_pool().acquire() as conn:
            await conn.execute("SELECT 1")
        health_status["postgresql"] = "healthy"
    except Exception as e:
        health_status["postgresql"] = f"unhealthy: {e}"
    
    try:
        # Elasticsearch health check
        await get_elasticsearch_client().ping()
        health_status["elasticsearch"] = "healthy"
    except Exception as e:
        health_status["elasticsearch"] = f"unhealthy: {e}"
    
    try:
        # Qdrant health check
        await get_qdrant_client().get_collections()
        health_status["qdrant"] = "healthy"
    except Exception as e:
        health_status["qdrant"] = f"unhealthy: {e}"
    
    try:
        # Neo4j health check
        async with get_neo4j_driver().session() as session:
            await session.run("RETURN 1")
        health_status["neo4j"] = "healthy"
    except Exception as e:
        health_status["neo4j"] = f"unhealthy: {e}"
    
    try:
        # Redis health check
        await get_redis_client().ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {e}"
    
    try:
        # MinIO health check
        get_minio_client().list_buckets()
        health_status["minio"] = "healthy"
    except Exception as e:
        health_status["minio"] = f"unhealthy: {e}"
    
    return health_status 