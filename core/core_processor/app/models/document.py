"""
Document models for the Core Processor
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # New descriptive statuses for better visibility
    INITIALIZING = "initializing"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    FINALIZING = "finalizing"
    TEXT_EXTRACTION_FAILED = "text_extraction_failed"
    EMBEDDING_GENERATION_FAILED = "embedding_generation_failed"


class DocumentType(str, Enum):
    """Document types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ProcessingStep(str, Enum):
    """Processing steps"""
    TEXT_EXTRACTION = "text_extraction"
    METADATA_EXTRACTION = "metadata_extraction"
    EMBEDDING_GENERATION = "embedding_generation"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    CLIMATE_ANALYSIS = "climate_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    LEGAL_ANALYSIS = "legal_analysis"


class JobStatus(str, Enum):
    """Processing job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    id: Optional[UUID] = Field(default_factory=uuid4)
    filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str] = None
    file_hash: str
    source: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    document_type: Optional[DocumentType] = None
    company: Optional[str] = None
    year: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ProcessingJob(BaseModel):
    """Processing job model"""
    id: Optional[UUID] = Field(default_factory=uuid4)
    document_id: UUID
    job_type: ProcessingStep
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentContent(BaseModel):
    """Document content model"""
    document_id: UUID
    text_content: str
    extracted_tables: List[Dict[str, Any]] = Field(default_factory=list)
    layout_info: Dict[str, Any] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentEmbedding(BaseModel):
    """Document embedding model"""
    document_id: UUID
    embedding_id: Optional[UUID] = Field(default_factory=uuid4)
    embedding_vector: List[float]
    embedding_model: str
    chunk_text: str
    chunk_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentEntity(BaseModel):
    """Document entity model"""
    document_id: UUID
    entity_id: Optional[UUID] = Field(default_factory=uuid4)
    entity_type: str
    entity_value: str
    confidence_score: float
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentRelationship(BaseModel):
    """Document relationship model"""
    id: Optional[UUID] = Field(default_factory=uuid4)
    source_document_id: UUID
    target_document_id: UUID
    relationship_type: str
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClimateData(BaseModel):
    """Climate analysis data model"""
    document_id: UUID
    emissions: List[Dict[str, Any]] = Field(default_factory=list)
    targets: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    strategy: Dict[str, Any] = Field(default_factory=dict)
    compliance: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FinancialData(BaseModel):
    """Financial analysis data model"""
    document_id: UUID
    income_statement: Dict[str, Any] = Field(default_factory=dict)
    balance_sheet: Dict[str, Any] = Field(default_factory=dict)
    cash_flow: Dict[str, Any] = Field(default_factory=dict)
    ratios: Dict[str, Any] = Field(default_factory=dict)
    trends: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingResult(BaseModel):
    """Processing result model"""
    document_id: UUID
    processing_step: ProcessingStep
    success: bool
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SystemStats(BaseModel):
    """System statistics model"""
    total_documents: int
    documents_by_status: Dict[str, int]
    documents_by_type: Dict[str, int]
    processing_jobs_by_status: Dict[str, int]
    average_processing_time: Optional[float] = None
    storage_usage: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow) 