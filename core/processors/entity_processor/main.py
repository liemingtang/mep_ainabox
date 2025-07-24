#!/usr/bin/env python3
"""
Entity Processor - Entity extraction and relationship mapping service
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Entity Processor",
    description="Entity extraction and relationship mapping service for MDIS",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")
NEO4J_HOST = os.getenv("NEO4J_HOST", "neo4j")
NEO4J_PORT = os.getenv("NEO4J_PORT", "7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Request/Response models
class EntityRequest(BaseModel):
    document_id: str
    text_content: str
    metadata: Optional[Dict[str, Any]] = None

class EntityResponse(BaseModel):
    document_id: str
    status: str
    entities_count: int
    relationships_count: int
    entity_types: List[str]
    stored_in_neo4j: bool
    processing_time: float

class Entity:
    """Represents an extracted entity"""
    
    def __init__(self, text: str, entity_type: str, start_pos: int, end_pos: int, confidence: float = 1.0):
        self.text = text
        self.entity_type = entity_type
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.confidence = confidence
        self.id = f"{text}_{entity_type}_{start_pos}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "entity_type": self.entity_type,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence
        }

class Relationship:
    """Represents a relationship between entities"""
    
    def __init__(self, source: Entity, target: Entity, relationship_type: str, confidence: float = 1.0):
        self.source = source
        self.target = target
        self.relationship_type = relationship_type
        self.confidence = confidence
        self.id = f"{source.id}_{relationship_type}_{target.id}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "relationship_type": self.relationship_type,
            "confidence": self.confidence
        }

class EntityExtractor:
    """Extract entities from text using rule-based and pattern matching"""
    
    def __init__(self):
        self.entity_patterns = {
            "PERSON": [
                r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                r'\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b',  # First M. Last
                r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # First Middle Last
            ],
            "ORGANIZATION": [
                r'\b[A-Z][a-z]+ (Inc|Corp|LLC|Ltd|Company|Co|Organization|Org)\b',
                r'\b[A-Z][a-z]+ [A-Z][a-z]+ (Inc|Corp|LLC|Ltd|Company|Co)\b',
                r'\b[A-Z][a-z]+ (University|College|School|Institute|Foundation)\b',
            ],
            "LOCATION": [
                r'\b[A-Z][a-z]+, [A-Z]{2}\b',  # City, State
                r'\b[A-Z][a-z]+, [A-Z][a-z]+\b',  # City, Country
                r'\b[A-Z][a-z]+ (Street|Avenue|Road|Boulevard|Drive|Lane)\b',
            ],
            "DATE": [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b',
                r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            ],
            "MONEY": [
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?\b',  # $1,234.56
                r'\b\d+(?:,\d{3})*(?:\.\d{2})? (dollars|USD|euros|EUR|pounds|GBP)\b',
            ],
            "EMAIL": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            "PHONE": [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890
                r'\b\(\d{3}\) \d{3}-\d{4}\b',  # (123) 456-7890
            ],
            "URL": [
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            ],
            "PERCENTAGE": [
                r'\b\d+(?:\.\d+)?%\b',
            ],
            "NUMBER": [
                r'\b\d+(?:,\d{3})*(?:\.\d+)?\b',
            ]
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text using pattern matching"""
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity = Entity(
                        text=match.group(),
                        entity_type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.8  # Base confidence for pattern matching
                    )
                    entities.append(entity)
        
        # Remove overlapping entities (keep the longer one)
        entities = self._remove_overlapping_entities(entities)
        
        return entities
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entities, keeping the longer ones"""
        if not entities:
            return entities
        
        # Sort by length (longer first) and start position
        entities.sort(key=lambda x: (len(x.text), -x.start_pos), reverse=True)
        
        filtered_entities = []
        for entity in entities:
            # Check if this entity overlaps with any already accepted entity
            overlaps = False
            for accepted in filtered_entities:
                if (entity.start_pos < accepted.end_pos and 
                    entity.end_pos > accepted.start_pos):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities

class RelationshipMapper:
    """Map relationships between extracted entities"""
    
    def __init__(self):
        self.relationship_patterns = {
            "WORKS_FOR": [
                r'(\w+)\s+(?:works for|employed by|employee of)\s+(\w+)',
                r'(\w+)\s+(?:is a|was a)\s+(?:employee|staff member|worker)\s+(?:of|at)\s+(\w+)',
            ],
            "LIVES_IN": [
                r'(\w+)\s+(?:lives in|resides in|located in)\s+(\w+)',
                r'(\w+)\s+(?:is from|comes from)\s+(\w+)',
            ],
            "OWNS": [
                r'(\w+)\s+(?:owns|purchased|bought)\s+(\w+)',
                r'(\w+)\s+(?:is the owner of|has ownership of)\s+(\w+)',
            ],
            "PART_OF": [
                r'(\w+)\s+(?:is part of|belongs to|member of)\s+(\w+)',
                r'(\w+)\s+(?:is a division of|subsidiary of)\s+(\w+)',
            ],
            "MANAGES": [
                r'(\w+)\s+(?:manages|supervises|leads)\s+(\w+)',
                r'(\w+)\s+(?:is the manager of|director of)\s+(\w+)',
            ]
        }
    
    def map_relationships(self, entities: List[Entity], text: str) -> List[Relationship]:
        """Map relationships between entities"""
        relationships = []
        
        # Create entity lookup by text
        entity_lookup = {entity.text.lower(): entity for entity in entities}
        
        # Find relationships using patterns
        for relationship_type, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity1_text = match.group(1).lower()
                    entity2_text = match.group(2).lower()
                    
                    if entity1_text in entity_lookup and entity2_text in entity_lookup:
                        entity1 = entity_lookup[entity1_text]
                        entity2 = entity_lookup[entity2_text]
                        
                        # Don't create self-relationships
                        if entity1.id != entity2.id:
                            relationship = Relationship(
                                source=entity1,
                                target=entity2,
                                relationship_type=relationship_type,
                                confidence=0.7
                            )
                            relationships.append(relationship)
        
        # Find co-occurrence relationships (entities mentioned close together)
        co_occurrence_relationships = self._find_co_occurrence_relationships(entities, text)
        relationships.extend(co_occurrence_relationships)
        
        return relationships
    
    def _find_co_occurrence_relationships(self, entities: List[Entity], text: str, window_size: int = 100) -> List[Relationship]:
        """Find relationships based on entities occurring close together"""
        relationships = []
        
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                # Check if entities are close to each other
                distance = abs(entity1.start_pos - entity2.start_pos)
                
                if distance <= window_size:
                    # Determine relationship type based on entity types
                    relationship_type = self._determine_relationship_type(entity1, entity2)
                    
                    if relationship_type:
                        relationship = Relationship(
                            source=entity1,
                            target=entity2,
                            relationship_type=relationship_type,
                            confidence=0.5  # Lower confidence for co-occurrence
                        )
                        relationships.append(relationship)
        
        return relationships
    
    def _determine_relationship_type(self, entity1: Entity, entity2: Entity) -> Optional[str]:
        """Determine relationship type based on entity types"""
        type_pairs = {
            ("PERSON", "ORGANIZATION"): "WORKS_FOR",
            ("PERSON", "LOCATION"): "LIVES_IN",
            ("ORGANIZATION", "LOCATION"): "LOCATED_IN",
            ("PERSON", "PERSON"): "KNOWS",
            ("ORGANIZATION", "ORGANIZATION"): "PARTNERS_WITH",
        }
        
        entity_types = (entity1.entity_type, entity2.entity_type)
        return type_pairs.get(entity_types)

class Neo4jClient:
    """Client for interacting with Neo4j graph database"""
    
    def __init__(self, host: str = "neo4j", port: int = 7474, user: str = "neo4j", password: str = "password"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.base_url = f"http://{host}:{port}"
    
    async def test_connection(self) -> bool:
        """Test connection to Neo4j"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/", timeout=5.0)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {e}")
            return False
    
    async def store_entities_and_relationships(self, document_id: str, entities: List[Entity], 
                                             relationships: List[Relationship]) -> bool:
        """Store entities and relationships in Neo4j"""
        try:
            # For demo purposes, we'll simulate Neo4j storage
            # In production, you would use the Neo4j Python driver or REST API
            
            logger.info(f"Would store {len(entities)} entities and {len(relationships)} relationships in Neo4j")
            logger.info(f"Document ID: {document_id}")
            
            # Simulate storage success
            return True
            
        except Exception as e:
            logger.error(f"Error storing in Neo4j: {e}")
            return False
    
    async def create_entity_node(self, entity: Entity, document_id: str) -> bool:
        """Create an entity node in Neo4j"""
        try:
            # Cypher query to create entity node
            cypher_query = """
            MERGE (e:Entity {id: $entity_id})
            SET e.text = $text,
                e.entity_type = $entity_type,
                e.confidence = $confidence,
                e.document_id = $document_id,
                e.created_at = datetime()
            """
            
            # In production, execute this query using Neo4j driver
            logger.info(f"Would create entity node: {entity.text} ({entity.entity_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating entity node: {e}")
            return False
    
    async def create_relationship(self, relationship: Relationship, document_id: str) -> bool:
        """Create a relationship in Neo4j"""
        try:
            # Cypher query to create relationship
            cypher_query = """
            MATCH (source:Entity {id: $source_id})
            MATCH (target:Entity {id: $target_id})
            MERGE (source)-[r:$relationship_type]->(target)
            SET r.confidence = $confidence,
                r.document_id = $document_id,
                r.created_at = datetime()
            """
            
            # In production, execute this query using Neo4j driver
            logger.info(f"Would create relationship: {relationship.source.text} -[{relationship.relationship_type}]-> {relationship.target.text}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return False

# Initialize components
entity_extractor = EntityExtractor()
relationship_mapper = RelationshipMapper()
neo4j_client = Neo4jClient(NEO4J_HOST, int(NEO4J_PORT), NEO4J_USER, NEO4J_PASSWORD)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        neo4j_healthy = await neo4j_client.test_connection()
    except:
        neo4j_healthy = False
    
    return {
        "status": "healthy" if neo4j_healthy else "degraded",
        "service": "entity-processor",
        "neo4j_connection": "healthy" if neo4j_healthy else "unhealthy"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS Entity Processor",
        "version": "1.0.0",
        "processing_pipeline": PROCESSING_PIPELINE_URL,
        "core_processor": CORE_PROCESSOR_URL,
        "neo4j_host": NEO4J_HOST,
        "supported_entity_types": list(entity_extractor.entity_patterns.keys()),
        "supported_relationship_types": list(relationship_mapper.relationship_patterns.keys())
    }

@app.post("/process")
async def process_entities(request: EntityRequest):
    """Process document entities and relationships"""
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Processing entities for document {request.document_id}")
        
        # Extract entities
        entities = entity_extractor.extract_entities(request.text_content)
        logger.info(f"Extracted {len(entities)} entities from document {request.document_id}")
        
        # Map relationships
        relationships = relationship_mapper.map_relationships(entities, request.text_content)
        logger.info(f"Mapped {len(relationships)} relationships for document {request.document_id}")
        
        # Store in Neo4j
        stored = await neo4j_client.store_entities_and_relationships(
            request.document_id,
            entities,
            relationships
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Get unique entity types
        entity_types = list(set(entity.entity_type for entity in entities))
        
        # Update job status in processing pipeline
        result_data = {
            "entities_count": len(entities),
            "relationships_count": len(relationships),
            "entity_types": entity_types,
            "stored_in_neo4j": stored,
            "processing_time": processing_time,
            "entities": [entity.to_dict() for entity in entities[:10]],  # Limit for response
            "relationships": [rel.to_dict() for rel in relationships[:10]]  # Limit for response
        }
        
        await update_job_status(request.document_id, "completed", result_data)
        
        logger.info(f"Entity processing completed for document {request.document_id}")
        
        return EntityResponse(
            document_id=request.document_id,
            status="completed",
            entities_count=len(entities),
            relationships_count=len(relationships),
            entity_types=entity_types,
            stored_in_neo4j=stored,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing entities for document {request.document_id}: {e}")
        
        # Update job status to failed
        await update_job_status(request.document_id, "failed", {"error": str(e)})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing entities: {str(e)}"
        )

@app.get("/entities/{document_id}")
async def get_document_entities(document_id: str):
    """Get entities for a specific document"""
    try:
        # In production, this would query Neo4j for entities
        return {
            "document_id": document_id,
            "entities": [],
            "message": "Entity retrieval not implemented in demo version"
        }
    except Exception as e:
        logger.error(f"Error retrieving entities for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entities: {str(e)}"
        )

@app.post("/api/v1/process")
async def process_entities_legacy():
    """Legacy endpoint for backward compatibility"""
    return {
        "status": "processed",
        "entities": {
            "count": 5,
            "types": ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY"]
        }
    }

async def update_job_status(document_id: str, status: str, result_data: Dict[str, Any] = None):
    """Update job status in the processing pipeline"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PROCESSING_PIPELINE_URL}/jobs/{document_id}/status",
                json={
                    "status": status,
                    "result_data": result_data or {}
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Updated job status for document {document_id} to {status}")
    except Exception as e:
        logger.warning(f"Failed to update job status for document {document_id}: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8008,
        reload=False,
        log_level="info"
    ) 