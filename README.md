# MEP AI NABOX

A comprehensive AI-powered file scanning and analysis system that allows users to point to any folder on their system, scan all files, and create a rich collection of information for natural language queries and advanced search capabilities.

## 🎯 System Overview

MEP AI NABOX is designed to be a universal file intelligence system that:

- **Scans any folder** on the user's system recursively
- **Processes all file types** including documents, images, videos, and binary files
- **Generates rich metadata** using custom AI analysis for each file
- **Enables natural language queries** across the entire scanned dataset
- **Supports extensible data sources** (files, databases, emails, etc.)
- **Provides photo understanding** through custom vision analysis
- **Self-contained architecture** with no dependencies on other MEP projects

## 🏗️ Architecture

### Core Components

#### 1. **File Scanner Engine** (`/scanner`)
- **Recursive Directory Traversal**: Scan entire folder structures
- **File Type Detection**: Automatic format recognition
- **Metadata Extraction**: File properties, timestamps, permissions
- **Incremental Scanning**: Only process new/modified files
- **Progress Tracking**: Real-time scan progress monitoring

#### 2. **AI Analysis Pipeline** (`/analysis`)
- **Document Processing**: Text extraction from PDFs, DOCX, TXT, etc.
- **Image Analysis**: OCR, object detection, scene understanding
- **Video Processing**: Frame extraction, audio transcription
- **Content Classification**: AI-powered categorization
- **Entity Extraction**: Names, dates, locations, values
- **Custom LLM Integration**: Self-contained AI processing

#### 3. **Advanced Storage System** (`/storage`)
- **Multi-Embedding Support**: Generate and store multiple embeddings per file
- **Elasticsearch Integration**: Full-text search capabilities
- **Qdrant Integration**: High-performance vector database
- **Graph Database**: Neo4j for relationship mapping and reasoning
- **Metadata Indexing**: Structured data for filtering
- **Cross-Reference Linking**: Connect related files and content
- **RAG Pipeline**: Retrieval-Augmented Generation for enhanced search

#### 4. **Advanced Query Interface** (`/query`)
- **Natural Language Processing**: Convert questions to search queries
- **Hybrid Search**: Combine full-text, vector, and graph search
- **Multi-Embedding Search**: Search across different embedding models
- **Graph Reasoning**: Find relationships and connections between files
- **RAG Integration**: Enhanced responses with retrieved context
- **Filtered Queries**: Search by file type, date, category, etc.
- **Conversational Interface**: Chat-based interaction with data
- **Query Optimization**: Intelligent query routing and result ranking

#### 5. **Extensible Data Sources** (`/connectors`)
- **File System Connector**: Current implementation
- **Database Connector**: Future - SQL, NoSQL databases
- **Email Connector**: Future - IMAP, Exchange integration
- **Cloud Storage Connector**: Future - S3, Google Drive, etc.

## 🚀 Implementation Plan

### Phase 1: Core File Scanner (Week 1-2)
```bash
# Directory structure
mep_ainabox/
├── scanner/
│   ├── file_scanner.py          # Main scanning engine
│   ├── file_processor.py        # File type detection & processing
│   ├── metadata_extractor.py    # File metadata extraction
│   └── progress_tracker.py      # Scan progress monitoring
├── analysis/
│   ├── document_analyzer.py     # Text document analysis
│   ├── image_analyzer.py        # Image/photo analysis
│   ├── video_analyzer.py        # Video content analysis
│   ├── content_classifier.py    # AI-powered categorization
│   ├── llm_client.py            # Custom LLM integration
│   ├── vision_client.py         # Custom vision model integration
│   └── embedding_generator.py   # Vector embedding generation
├── storage/
│   ├── vector_store.py          # Qdrant integration
│   ├── elasticsearch_store.py   # Elasticsearch integration
│   ├── graph_store.py           # Neo4j graph database
│   ├── metadata_store.py        # SQLite/PostgreSQL for metadata
│   ├── index_manager.py         # Search index management
│   ├── embedding_manager.py     # Multi-embedding management
│   └── rag_pipeline.py          # RAG implementation
├── query/
│   ├── query_engine.py          # Natural language query processing
│   ├── hybrid_search.py         # Combined search strategies
│   ├── graph_reasoning.py       # Graph-based reasoning
│   ├── multi_embedding_search.py # Multi-embedding search
│   ├── search_interface.py      # Search API endpoints
│   ├── chat_interface.py        # Conversational query interface
│   └── query_optimizer.py       # Query optimization and routing
├── api/
│   ├── main.py                  # FastAPI application
│   ├── scan_endpoints.py        # File scanning endpoints
│   ├── query_endpoints.py       # Search and query endpoints
│   └── analysis_endpoints.py    # AI analysis endpoints
├── config/
│   ├── settings.py              # Configuration management
│   ├── file_types.py            # Supported file type definitions
│   ├── ai_models.py             # AI model configurations
│   └── llm_config.py            # LLM and vision model settings
├── tests/
│   ├── test_scanner.py          # Scanner unit tests
│   ├── test_analysis.py         # Analysis pipeline tests
│   └── test_query.py            # Query engine tests
├── docker/
│   ├── Dockerfile               # Main application container
│   ├── docker-compose.yml       # Complete service stack
│   └── entrypoint.sh            # Container startup script
└── docs/
    ├── API.md                   # API documentation
    ├── DEPLOYMENT.md            # Deployment guide
    └── USAGE.md                 # User guide
```

### Phase 2: AI Analysis Integration (Week 3-4)
- Build custom AI analysis pipeline from scratch
- Add image analysis using vision models
- Implement video processing pipeline
- Create content classification system

### Phase 3: Advanced Query Interface (Week 5-6)
- Build hybrid search engine (full-text + vector + graph)
- Implement multi-embedding search capabilities
- Create graph reasoning and relationship mapping
- Integrate RAG pipeline for enhanced responses
- Build conversational chat interface with RAG
- Implement query optimization and intelligent routing
- Add advanced search filters and result ranking

### Phase 4: Extensibility & Optimization (Week 7-8)
- Design connector framework for future data sources
- Optimize performance for large file collections
- Add incremental scanning capabilities
- Implement caching and optimization
- Fine-tune multi-embedding strategies
- Optimize graph database queries
- Implement advanced RAG techniques

## 🔧 Technical Implementation

### File Scanner Engine
```python
class FileScanner:
    def __init__(self, root_path: str, config: ScanConfig):
        self.root_path = Path(root_path)
        self.config = config
        self.processor = FileProcessor()
        self.analyzer = ContentAnalyzer()
    
    async def scan_directory(self) -> ScanResult:
        """Recursively scan directory and process all files"""
        files = []
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                file_info = await self.processor.process_file(file_path)
                if file_info:
                    files.append(file_info)
        return ScanResult(files=files)
```

### AI Analysis Pipeline
```python
class ContentAnalyzer:
    def __init__(self, llm_client: LLMClient, vision_client: VisionClient):
        self.llm_client = llm_client
        self.vision_client = vision_client
        self.document_analyzer = DocumentAnalyzer(llm_client)
        self.image_analyzer = ImageAnalyzer(vision_client)
        self.video_analyzer = VideoAnalyzer(vision_client)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def analyze_file(self, file_info: FileInfo) -> AnalysisResult:
        """Analyze file content based on type"""
        if file_info.is_document:
            return await self.document_analyzer.analyze(file_info)
        elif file_info.is_image:
            return await self.image_analyzer.analyze(file_info)
        elif file_info.is_video:
            return await self.video_analyzer.analyze(file_info)
        else:
            return await self.generic_analyzer.analyze(file_info)
```

### Advanced Query Engine
```python
class AdvancedQueryEngine:
    def __init__(self, 
                 vector_store: VectorStore, 
                 elasticsearch_store: ElasticsearchStore,
                 graph_store: GraphStore,
                 embedding_manager: EmbeddingManager,
                 rag_pipeline: RAGPipeline):
        self.vector_store = vector_store
        self.elasticsearch_store = elasticsearch_store
        self.graph_store = graph_store
        self.embedding_manager = embedding_manager
        self.rag_pipeline = rag_pipeline
        self.hybrid_search = HybridSearch()
        self.graph_reasoning = GraphReasoning()
        self.query_optimizer = QueryOptimizer()
    
    async def natural_language_query(self, query: str, 
                                   search_strategy: str = "hybrid",
                                   embeddings: List[str] = None) -> QueryResult:
        """Process natural language query with advanced search capabilities"""
        # Parse and optimize query
        search_params = await self.query_optimizer.optimize_query(query)
        
        # Determine search strategy
        if search_strategy == "hybrid":
            results = await self.hybrid_search.search(
                query=search_params,
                embeddings=embeddings or ["default", "domain_specific"]
            )
        elif search_strategy == "graph":
            results = await self.graph_reasoning.search(
                query=search_params,
                depth=3
            )
        else:
            results = await self.vector_store.similarity_search(
                query=search_params.embedding_query,
                filters=search_params.filters,
                limit=search_params.limit
            )
        
        # Enhance with RAG
        enhanced_results = await self.rag_pipeline.enhance_results(results, query)
        
        return enhanced_results
```

## 🎯 Key Features

### 1. **Universal File Support**
- **Documents**: PDF, DOCX, TXT, CSV, RTF, ODT
- **Images**: JPG, PNG, GIF, BMP, TIFF, WebP
- **Videos**: MP4, AVI, MOV, MKV, WebM
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Archives**: ZIP, RAR, 7Z, TAR, GZ
- **Code**: All programming language files
- **Binary**: Any other file type with metadata extraction

### 2. **AI-Powered Analysis**
- **Document Understanding**: Extract text, structure, and meaning using custom LLM integration
- **Image Recognition**: Objects, scenes, text (OCR), faces using vision models
- **Video Analysis**: Key frames, audio transcription, content summary
- **Content Classification**: Automatic categorization and tagging
- **Entity Extraction**: Names, dates, locations, values, relationships
- **Vector Embeddings**: Generate searchable embeddings for all content types

### 3. **Advanced Search Capabilities**
- **Natural Language Queries**: "Find all documents about project X"
- **Hybrid Search**: Combine full-text, vector, and graph search strategies
- **Multi-Embedding Search**: Search across different embedding models simultaneously
- **Graph Reasoning**: Find relationships and connections between files
- **RAG Integration**: Enhanced responses with retrieved context and reasoning
- **Filtered Search**: By file type, date, size, category, etc.
- **Conversational Interface**: Chat with your data using RAG
- **Cross-Reference Search**: Find related files and content through graph relationships
- **Query Optimization**: Intelligent routing and result ranking

### 4. **Extensible Architecture**
- **Plugin System**: Easy addition of new file types
- **Connector Framework**: Future database and email integration
- **API-First Design**: RESTful API for all operations
- **Modular Components**: Independent, testable modules
- **Self-Contained**: No external dependencies on other MEP projects

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- At least 12GB RAM (for AI models and search engines)
- OpenAI API key (or compatible LLM provider)
- HuggingFace API token (for model access)
- Elasticsearch 8.x (for full-text search)
- Neo4j 5.x (for graph database)

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd mep_ainabox

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start services
docker-compose up -d

# Scan a directory
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/folder"}'

# Query your data with advanced search
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find all documents about machine learning",
    "search_strategy": "hybrid",
    "embeddings": ["default", "domain_specific"],
    "include_graph_reasoning": true
  }'
```

## 🔮 Future Enhancements

### Phase 2: Database Integration
- **SQL Database Connector**: Scan and analyze database schemas
- **NoSQL Database Connector**: MongoDB, Redis, etc.
- **Query Analysis**: Understand database queries and relationships

### Phase 3: Email Integration
- **IMAP Connector**: Scan email accounts
- **Exchange Connector**: Enterprise email integration
- **Email Thread Analysis**: Conversation threading and analysis

### Phase 4: Cloud Storage
- **S3 Connector**: Amazon S3 bucket scanning
- **Google Drive Connector**: Google Drive integration
- **OneDrive Connector**: Microsoft OneDrive support

### Phase 5: Advanced AI & Search
- **Multi-Modal Analysis**: Combine text, image, and video understanding
- **Temporal Analysis**: Track changes over time
- **Predictive Analytics**: Identify patterns and trends
- **Automated Insights**: Generate reports and recommendations
- **Advanced RAG**: Multi-step reasoning and chain-of-thought
- **Graph Analytics**: Network analysis and community detection
- **Embedding Optimization**: Domain-specific embedding fine-tuning

## 📊 Performance Considerations

### Scalability
- **Incremental Scanning**: Only process new/modified files
- **Parallel Processing**: Multi-threaded file analysis
- **Distributed Processing**: Celery for background tasks
- **Caching**: Redis for frequently accessed data

### Storage Optimization
- **Multi-Embedding Storage**: Efficient storage of multiple embeddings per file
- **Vector Compression**: Optimize embedding storage
- **Elasticsearch Optimization**: Index optimization and sharding
- **Graph Database Optimization**: Neo4j query optimization and indexing
- **Metadata Indexing**: Efficient metadata queries
- **Content Deduplication**: Avoid storing duplicate content
- **Archive Management**: Compress old data

### AI Model Optimization
- **Model Caching**: Cache loaded AI models locally
- **Batch Processing**: Process multiple files together
- **Model Selection**: Choose appropriate models for file types
- **Fallback Models**: Graceful degradation for unavailable models
- **Local Model Support**: Run models locally when possible
- **API Rate Limiting**: Manage external API usage efficiently

## 🤝 Contributing

This project is designed to be highly extensible. Key areas for contribution:

1. **File Type Processors**: Add support for new file formats
2. **AI Analysis Modules**: Improve content understanding
3. **Search Enhancements**: Better hybrid search algorithms
4. **Embedding Models**: Add new embedding strategies
5. **Graph Algorithms**: Improve relationship detection and reasoning
6. **RAG Improvements**: Enhanced retrieval and generation techniques
7. **Performance Optimizations**: Faster scanning and analysis
8. **New Connectors**: Database, email, cloud storage integration

## 📄 License

[License information to be added]    
