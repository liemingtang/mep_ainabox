"""
Document service for managing document metadata and operations
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID

import asyncpg
from elasticsearch import AsyncElasticsearch

from app.database import get_postgres_pool, get_elasticsearch_client
from app.logging import LoggerMixin
from app.models.document import (
    DocumentMetadata, ProcessingStatus, DocumentType, SystemStats
)


class DocumentService(LoggerMixin):
    """Service for managing document metadata and operations"""
    
    def __init__(self):
        self.postgres_pool = get_postgres_pool()
        self.elasticsearch_client = get_elasticsearch_client()
    
    async def create_document(self, document: DocumentMetadata) -> UUID:
        """Create a new document record"""
        try:
            self.logger.info(f"Creating document: {document.filename}")
            
            # Generate file hash if not provided
            if not document.file_hash:
                document.file_hash = await self._generate_file_hash(document.file_path)
            
            # Detect document type if not provided
            if not document.document_type:
                document.document_type = self._detect_document_type(document.filename)
            
            # Store in PostgreSQL
            doc_id = await self._store_document_metadata(document)
            
            # Index in Elasticsearch
            await self._index_document_elasticsearch(doc_id, document)
            
            self.logger.info(f"Document created successfully: {doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to create document: {e}")
            raise
    
    async def get_document(self, document_id: UUID) -> Optional[DocumentMetadata]:
        """Get document by ID"""
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM documents WHERE id = $1
                    """,
                    str(document_id)
                )
                
                if row:
                    # Convert JSONB fields back to dicts
                    row_dict = dict(row)
                    if isinstance(row_dict.get('metadata'), str):
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    return DocumentMetadata(**row_dict)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {e}")
            raise
    
    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List[DocumentMetadata]:
        """List documents with optional filtering"""
        try:
            query = "SELECT * FROM documents WHERE 1=1"
            params = []
            param_count = 0
            
            if status:
                param_count += 1
                query += f" AND processing_status = ${param_count}"
                params.append(status)
            
            if document_type:
                param_count += 1
                query += f" AND document_type = ${param_count}"
                params.append(document_type)
            
            query += " ORDER BY created_at DESC LIMIT $%d OFFSET $%d" % (param_count + 1, param_count + 2)
            params.extend([limit, skip])
            
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                documents = []
                for row in rows:
                    # Convert JSONB fields back to dicts
                    row_dict = dict(row)
                    if isinstance(row_dict.get('metadata'), str):
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    documents.append(DocumentMetadata(**row_dict))
                return documents
                
        except Exception as e:
            self.logger.error(f"Failed to list documents: {e}")
            raise
    
    async def update_document_status(
        self,
        document_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update document processing status"""
        try:
            async with self.postgres_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE documents 
                    SET processing_status = $1, 
                        error_message = $2, 
                        updated_at = $3,
                        processed_at = CASE WHEN $1 = 'completed' THEN $3 ELSE processed_at END
                    WHERE id = $4
                    """,
                    status.value,
                    error_message,
                    datetime.utcnow(),
                    str(document_id)
                )
                
                return result.split()[-1] == "1"
                
        except Exception as e:
            self.logger.error(f"Failed to update document status: {e}")
            raise
    
    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document and all associated data"""
        try:
            self.logger.info(f"Deleting document: {document_id}")
            
            # Get document info first
            document = await self.get_document(document_id)
            if not document:
                return False
            
            async with self.postgres_pool.acquire() as conn:
                # Delete from PostgreSQL
                await conn.execute(
                    "DELETE FROM documents WHERE id = $1",
                    str(document_id)
                )
            
            # Remove from Elasticsearch
            try:
                await self.elasticsearch_client.delete(
                    index="documents",
                    id=str(document_id)
                )
            except Exception as e:
                self.logger.warning(f"Failed to remove from Elasticsearch: {e}")
            
            # Delete file from storage
            try:
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
            except Exception as e:
                self.logger.warning(f"Failed to delete file: {e}")
            
            self.logger.info(f"Document deleted successfully: {document_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete document: {e}")
            raise
    
    async def get_system_stats(self) -> SystemStats:
        """Get system statistics"""
        try:
            async with self.postgres_pool.acquire() as conn:
                # Total documents
                total_docs = await conn.fetchval("SELECT COUNT(*) FROM documents")
                
                # Documents by status
                status_stats = await conn.fetch(
                    "SELECT processing_status, COUNT(*) FROM documents GROUP BY processing_status"
                )
                documents_by_status = {row['processing_status']: row['count'] for row in status_stats}
                
                # Documents by type
                type_stats = await conn.fetch(
                    "SELECT document_type, COUNT(*) FROM documents GROUP BY document_type"
                )
                documents_by_type = {row['document_type']: row['count'] for row in type_stats}
                
                # Processing jobs by status
                job_stats = await conn.fetch(
                    "SELECT status, COUNT(*) FROM processing_jobs GROUP BY status"
                )
                processing_jobs_by_status = {row['status']: row['count'] for row in job_stats}
                
                # Average processing time
                avg_time = await conn.fetchval(
                    """
                    SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                    FROM processing_jobs 
                    WHERE status = 'completed' AND completed_at IS NOT NULL
                    """
                )
                
                return SystemStats(
                    total_documents=total_docs,
                    documents_by_status=documents_by_status,
                    documents_by_type=documents_by_type,
                    processing_jobs_by_status=processing_jobs_by_status,
                    average_processing_time=float(avg_time) if avg_time else None
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            raise
    
    async def _store_document_metadata(self, document: DocumentMetadata) -> UUID:
        """Store document metadata in PostgreSQL"""
        async with self.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (
                    id, filename, file_path, file_size, mime_type, file_hash,
                    source, processing_status, document_type, company, year,
                    metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
                """,
                str(document.id),
                document.filename,
                document.file_path,
                document.file_size,
                document.mime_type,
                document.file_hash,
                document.source,
                document.processing_status.value,
                document.document_type.value if document.document_type else None,
                document.company,
                document.year,
                json.dumps(document.metadata) if document.metadata else '{}',
                document.created_at,
                document.updated_at
            )
            
            return row['id']
    
    async def _index_document_elasticsearch(self, doc_id: UUID, document: DocumentMetadata):
        """Index document in Elasticsearch"""
        try:
            await self.elasticsearch_client.index(
                index="documents",
                id=str(doc_id),
                document={
                    "document_id": str(doc_id),
                    "filename": document.filename,
                    "file_path": document.file_path,
                    "file_size": document.file_size,
                    "mime_type": document.mime_type,
                    "document_type": document.document_type.value if document.document_type else None,
                    "company": document.company,
                    "year": document.year,
                    "processing_status": document.processing_status.value,
                    "metadata": document.metadata if isinstance(document.metadata, dict) else {},
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat()
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to index document in Elasticsearch: {e}")
    
    async def _generate_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _detect_document_type(self, filename: str) -> DocumentType:
        """Detect document type from filename"""
        extension = Path(filename).suffix.lower()
        
        if extension == '.pdf':
            return DocumentType.PDF
        elif extension == '.docx':
            return DocumentType.DOCX
        elif extension == '.txt':
            return DocumentType.TXT
        elif extension == '.html':
            return DocumentType.HTML
        elif extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return DocumentType.IMAGE
        else:
            return DocumentType.UNKNOWN 