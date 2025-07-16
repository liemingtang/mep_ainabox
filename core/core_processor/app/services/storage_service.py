"""
Storage service for managing data across multiple storage systems
"""

import json
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from elasticsearch import AsyncElasticsearch
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
import redis.asyncio as redis
from minio import Minio

from app.database import (
    get_elasticsearch_client, get_neo4j_driver, get_qdrant_client,
    get_redis_client, get_minio_client
)
from app.logging import LoggerMixin
from app.models.document import (
    DocumentContent, DocumentEmbedding, DocumentEntity,
    DocumentRelationship, ClimateData, FinancialData
)


class StorageService(LoggerMixin):
    """Service for managing data across multiple storage systems"""
    
    def __init__(self):
        self.elasticsearch_client = get_elasticsearch_client()
        self.neo4j_driver = get_neo4j_driver()
        self.qdrant_client = get_qdrant_client()
        self.redis_client = get_redis_client()
        self.minio_client = get_minio_client()
    
    async def store_document_content(self, content: DocumentContent) -> bool:
        """Store document content in Elasticsearch"""
        try:
            await self.elasticsearch_client.index(
                index="document_content",
                id=str(content.document_id),
                document={
                    "document_id": str(content.document_id),
                    "text_content": content.text_content,
                    "extracted_tables": content.extracted_tables,
                    "layout_info": content.layout_info,
                    "quality_score": content.quality_score,
                    "created_at": content.created_at.isoformat()
                }
            )
            
            self.logger.info(f"Document content stored: {content.document_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store document content: {e}")
            raise
    
    async def store_document_embedding(self, embedding: DocumentEmbedding) -> bool:
        """Store document embedding in Qdrant"""
        try:
            await self.qdrant_client.upsert(
                collection_name="document_embeddings",
                points=[{
                    "id": str(embedding.embedding_id),
                    "vector": embedding.embedding_vector,
                    "payload": {
                        "document_id": str(embedding.document_id),
                        "embedding_model": embedding.embedding_model,
                        "chunk_text": embedding.chunk_text,
                        "chunk_index": embedding.chunk_index,
                        "created_at": embedding.created_at.isoformat()
                    }
                }]
            )
            
            self.logger.info(f"Document embedding stored: {embedding.embedding_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store document embedding: {e}")
            raise
    
    async def store_document_entity(self, entity: DocumentEntity) -> bool:
        """Store document entity in Neo4j"""
        try:
            async with self.neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (e:Entity {
                        id: $entity_id,
                        type: $entity_type,
                        value: $entity_value
                    })
                    MERGE (d:Document {id: $document_id})
                    MERGE (d)-[:CONTAINS_ENTITY {confidence: $confidence}]->(e)
                    SET e.confidence_score = $confidence,
                        e.start_position = $start_pos,
                        e.end_position = $end_pos,
                        e.metadata = $metadata,
                        e.created_at = $created_at
                    """,
                    entity_id=str(entity.entity_id),
                    entity_type=entity.entity_type,
                    entity_value=entity.entity_value,
                    document_id=str(entity.document_id),
                    confidence=entity.confidence_score,
                    start_pos=entity.start_position,
                    end_pos=entity.end_position,
                    metadata=json.dumps(entity.metadata),
                    created_at=entity.created_at.isoformat()
                )
            
            self.logger.info(f"Document entity stored: {entity.entity_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store document entity: {e}")
            raise
    
    async def store_document_relationship(self, relationship: DocumentRelationship) -> bool:
        """Store document relationship in Neo4j"""
        try:
            async with self.neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (d1:Document {id: $source_id})
                    MERGE (d2:Document {id: $target_id})
                    MERGE (d1)-[r:RELATES_TO {
                        type: $relationship_type,
                        confidence: $confidence
                    }]->(d2)
                    SET r.metadata = $metadata,
                        r.created_at = $created_at
                    """,
                    source_id=str(relationship.source_document_id),
                    target_id=str(relationship.target_document_id),
                    relationship_type=relationship.relationship_type,
                    confidence=relationship.confidence_score,
                    metadata=json.dumps(relationship.metadata),
                    created_at=relationship.created_at.isoformat()
                )
            
            self.logger.info(f"Document relationship stored: {relationship.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store document relationship: {e}")
            raise
    
    async def store_climate_data(self, climate_data: ClimateData) -> bool:
        """Store climate analysis data"""
        try:
            # Store in Elasticsearch
            await self.elasticsearch_client.index(
                index="climate_data",
                id=str(climate_data.document_id),
                document={
                    "document_id": str(climate_data.document_id),
                    "emissions": climate_data.emissions,
                    "targets": climate_data.targets,
                    "risks": climate_data.risks,
                    "governance": climate_data.governance,
                    "strategy": climate_data.strategy,
                    "compliance": climate_data.compliance,
                    "created_at": climate_data.created_at.isoformat(),
                    "updated_at": climate_data.updated_at.isoformat()
                }
            )
            
            # Store embeddings in Qdrant for semantic search
            if climate_data.emissions or climate_data.targets or climate_data.risks:
                await self._store_climate_embeddings(climate_data)
            
            self.logger.info(f"Climate data stored: {climate_data.document_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store climate data: {e}")
            raise
    
    async def store_financial_data(self, financial_data: FinancialData) -> bool:
        """Store financial analysis data"""
        try:
            # Store in Elasticsearch
            await self.elasticsearch_client.index(
                index="financial_data",
                id=str(financial_data.document_id),
                document={
                    "document_id": str(financial_data.document_id),
                    "income_statement": financial_data.income_statement,
                    "balance_sheet": financial_data.balance_sheet,
                    "cash_flow": financial_data.cash_flow,
                    "ratios": financial_data.ratios,
                    "trends": financial_data.trends,
                    "created_at": financial_data.created_at.isoformat(),
                    "updated_at": financial_data.updated_at.isoformat()
                }
            )
            
            self.logger.info(f"Financial data stored: {financial_data.document_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store financial data: {e}")
            raise
    
    async def store_file_in_minio(self, file_path: str, object_name: str) -> bool:
        """Store file in MinIO object storage"""
        try:
            self.minio_client.fput_object(
                bucket_name="documents",
                object_name=object_name,
                file_path=file_path
            )
            
            self.logger.info(f"File stored in MinIO: {object_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store file in MinIO: {e}")
            raise
    
    async def cache_data(self, key: str, data: Any, ttl: int = 3600) -> bool:
        """Cache data in Redis"""
        try:
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(data, default=str)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache data: {e}")
            raise
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data from Redis"""
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached data: {e}")
            return None
    
    async def search_documents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search documents in Elasticsearch"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["text_content^2", "filename", "metadata.*"]
                                }
                            }
                        ]
                    }
                },
                "size": 20
            }
            
            if filters:
                search_body["query"]["bool"]["filter"] = []
                for field, value in filters.items():
                    search_body["query"]["bool"]["filter"].append({
                        "term": {field: value}
                    })
            
            response = await self.elasticsearch_client.search(
                index="document_content",
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "document_id": hit["_source"]["document_id"],
                    "score": hit["_score"],
                    "content": hit["_source"]
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            raise
    
    async def semantic_search(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search using Qdrant"""
        try:
            response = await self.qdrant_client.search(
                collection_name="document_embeddings",
                query_vector=query_vector,
                limit=limit
            )
            
            results = []
            for point in response:
                results.append({
                    "embedding_id": point.id,
                    "score": point.score,
                    "payload": point.payload
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to perform semantic search: {e}")
            raise
    
    async def graph_search(self, entity_type: str, entity_value: str) -> List[Dict[str, Any]]:
        """Perform graph search in Neo4j"""
        try:
            async with self.neo4j_driver.session() as session:
                result = await session.run(
                    """
                    MATCH (e:Entity {type: $entity_type, value: $entity_value})
                    MATCH (d:Document)-[:CONTAINS_ENTITY]->(e)
                    OPTIONAL MATCH (d)-[r:RELATES_TO]->(related:Document)
                    RETURN d.id as document_id, 
                           e.confidence_score as confidence,
                           collect(DISTINCT related.id) as related_documents
                    """,
                    entity_type=entity_type,
                    entity_value=entity_value
                )
                
                results = []
                async for record in result:
                    results.append({
                        "document_id": record["document_id"],
                        "confidence": record["confidence"],
                        "related_documents": record["related_documents"]
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to perform graph search: {e}")
            raise
    
    async def health_check(self) -> Dict[str, str]:
        """Perform health check on all storage systems"""
        health_status = {}
        
        try:
            # Elasticsearch health check
            await self.elasticsearch_client.ping()
            health_status["elasticsearch"] = "healthy"
        except Exception as e:
            health_status["elasticsearch"] = f"unhealthy: {e}"
        
        try:
            # Qdrant health check
            await self.qdrant_client.get_collections()
            health_status["qdrant"] = "healthy"
        except Exception as e:
            health_status["qdrant"] = f"unhealthy: {e}"
        
        try:
            # Neo4j health check
            async with self.neo4j_driver.session() as session:
                await session.run("RETURN 1")
            health_status["neo4j"] = "healthy"
        except Exception as e:
            health_status["neo4j"] = f"unhealthy: {e}"
        
        try:
            # Redis health check
            await self.redis_client.ping()
            health_status["redis"] = "healthy"
        except Exception as e:
            health_status["redis"] = f"unhealthy: {e}"
        
        try:
            # MinIO health check
            self.minio_client.list_buckets()
            health_status["minio"] = "healthy"
        except Exception as e:
            health_status["minio"] = f"unhealthy: {e}"
        
        return health_status
    
    async def _store_climate_embeddings(self, climate_data: ClimateData):
        """Store climate data embeddings for semantic search"""
        # This would generate embeddings for climate data and store them
        # Implementation depends on the specific embedding model used
        pass 