# Changelog

All notable changes to the MEP AI NABOX system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Web Dashboard System**: Complete web-based monitoring and management interface
  - **Host-based Dashboard**: Runs directly on host for better performance and access
  - **Admin Panel**: Web-based service management with one-click startup
  - **Real-time Monitoring**: Live service status, logs, and metrics
  - **Service Management**: Start, stop, and monitor all services through web interface
  - **Admin Startup Mode**: `start_admin.sh` script for easy system startup
  - **Host Dashboard Scripts**: `start_dashboard_host.sh` and `stop_dashboard_host.sh`
  - **Modern UI**: Responsive design with real-time updates and progress tracking
  - **Service Details**: Individual service monitoring with logs, metrics, and configuration
  - **Health Monitoring**: Automatic health checks and status updates
  - **Startup Progress**: Real-time startup logs with visual progress tracking
  - **Configuration Management**: Secure configuration viewing with sensitive data masking
  - **Log Streaming**: Real-time log streaming with syntax highlighting
  - **Metrics Collection**: Docker stats and service metrics collection
  - **Error Handling**: Comprehensive error handling and user feedback
- **File Watcher Service**: Complete implementation with full functionality
  - Real-time file monitoring using watchdog library
  - Automatic file detection and upload to core processor
  - File validation and metadata creation
  - Asynchronous processing with error handling
  - API endpoints for status monitoring and manual processing
  - Integration with document router and processing pipeline
  - Test and demo scripts for file watcher functionality
- **File Upload Checker Script**: `check_uploaded_files.sh` for monitoring uploaded files
  - Multiple view options (all, watch folder only, status summary, recent, failed)
  - File watcher status monitoring
  - Processing status tracking
  - Error reporting for failed uploads
- **Duplicate File Handling**: Automatic detection and handling of duplicate files
  - File hash-based duplicate detection
  - Graceful handling of duplicate uploads
  - Return existing document ID for duplicates
  - Error handling for duplicate key violations
- **Processing Pipeline Implementation**: Complete processing service with endpoints
  - `/process` endpoint for document processing
  - `/analyze` endpoint for document analysis
  - Job status update functionality
  - Integration with core processor
- **Document Router Implementation**: Complete routing service with endpoints
  - `/analyze` endpoint for document analysis
  - Intelligent document routing based on content
  - Integration with processing pipeline
- **Comprehensive .gitignore**: Complete file exclusion rules
  - Test files and error logs
  - Processing artifacts and temporary files
  - Log files and system artifacts
  - Development and build artifacts
- Comprehensive system test script (`test_system.py`)
- Simple upload test script (`test_simple_upload.py`)
- Upload-only test script (`test_upload_only.py`)
- File watcher test script (`test_file_watcher.py`)
- File watcher demo script (`demo_file_watcher.py`)
- Detailed logging and error reporting for all services
- Health check validation for all services
- JSON serialization for metadata fields in database operations
- UUID to string conversion utilities for database queries
- Environment variable loading improvements in startup scripts
- Service dependency management and startup sequence
- Prometheus metrics registration for monitoring
- Database connection pooling for PostgreSQL
- API key authentication for Qdrant vector database
- Structured JSON logging throughout the system
- File permission management in startup scripts
- Database schema initialization with proper UUID support

### Changed
- **Dashboard Architecture**: Moved from Docker-based to host-based dashboard
  - Dashboard now runs directly on host for better performance
  - Removed dashboard service from docker-compose.yml
  - Enhanced connectivity to local services and files
  - Improved startup scripts with virtual environment management
- **Startup Process**: Enhanced with admin mode and web-based management
  - New `start_admin.sh` script for easy system startup
  - Web-based service management through admin panel
  - Real-time startup progress monitoring
  - Improved service dependency management
- **Docker Compose Configuration**: Enhanced file watcher service configuration
  - Proper environment variables and volume mounts
  - Port mappings and network configuration
  - Health check and restart policies
- **Core Processor**: Enhanced document service with duplicate handling
  - File hash checking before document insertion
  - Duplicate key error handling in metadata storage
  - Improved error messages and logging
- **Processing Service**: Enhanced with complete endpoint implementation
  - Full processing pipeline integration
  - Job status update functionality
  - Error handling and logging improvements
- Updated all SQL queries to properly handle UUID types
- Improved database schema with proper UUID extensions
- Enhanced error handling in API endpoints
- Updated service startup sequence for better reliability
- Improved environment variable loading in containers
- Enhanced logging format with structured JSON
- Updated Docker Compose configuration for better service management
- Improved health check endpoints for all services
- Enhanced database connection handling across all services

### Fixed
- **Critical**: Dashboard template not found errors
- **Critical**: Dashboard running from wrong directory issues
- **Critical**: Docker container path resolution problems
- **Critical**: Dashboard connectivity to localhost services
- **Critical**: Admin panel startup log path resolution
- **Critical**: Dashboard permission and environment variable loading
- **Critical**: File watcher service startup and threading issues
- **Critical**: UUID serialization in processing service
- **Critical**: Datetime serialization in JSON operations
- **Critical**: Missing processing pipeline endpoints
- **Critical**: Missing document router endpoints
- **Critical**: Job status update endpoint in core processor
- **Critical**: Import errors in core processor middleware
- **Critical**: Duplicate key errors during file upload
- **Critical**: UUID type mismatch errors in all SQL queries
- **Critical**: JSON serialization issues for metadata fields
- **Critical**: Database schema initialization failures
- **Critical**: Service startup sequence issues
- **Critical**: Environment variable loading in startup scripts
- **Critical**: Prometheus metrics registration conflicts
- **Critical**: PostgreSQL connection pool initialization
- **Critical**: Elasticsearch client configuration errors
- **Critical**: Qdrant API key authentication issues
- **Critical**: Neo4j driver initialization problems
- **Critical**: Redis connection handling
- **Critical**: MinIO client setup issues
- **Critical**: File permission issues in mounted volumes
- **Critical**: Service health check endpoint failures
- **Critical**: API endpoint parameter handling for UUIDs
- **Critical**: Database connection timeout issues
- **Critical**: Service dependency resolution problems
- **Critical**: Container startup script execution issues
- **Critical**: Logging configuration in containers
- **Critical**: Network connectivity between services

### Security
- Added proper API key authentication for Qdrant
- Enhanced environment variable security
- Improved service-to-service communication security
- Added audit logging for database operations
- File validation in file watcher service

## [0.1.0] - 2024-07-16

### Added
- Initial implementation of Modular Document Intelligence System (MDIS)
- Core system architecture with microservices design
- API Gateway service for unified client interactions
- Core Processor service for document processing orchestration
- Document Router service for intelligent document routing
- Processing Pipeline service for orchestrated workflows
- Storage Manager service for unified data storage
- Text Processor service for text extraction
- Metadata Processor service for metadata extraction
- Embedding Processor service for vector embedding generation
- Entity Processor service for entity extraction
- File Watcher service for monitoring local folders
- PostgreSQL database for metadata storage
- Elasticsearch for full-text search
- Qdrant for vector similarity search
- Neo4j for graph relationships
- MinIO for object storage
- Redis for caching and session management
- Docker Compose configuration for all services
- Environment variable configuration system
- Basic health check endpoints
- Initial API endpoints for document operations
- Database schema with tables for documents, processing jobs, and results
- Basic logging system
- Initial test scripts

### Technical Details
- **Architecture**: Microservices with Docker containers
- **API Framework**: FastAPI for all services
- **Database**: PostgreSQL with UUID support
- **Search**: Elasticsearch for full-text, Qdrant for vectors
- **Graph**: Neo4j for relationships
- **Storage**: MinIO for objects, Redis for cache
- **Monitoring**: Prometheus metrics and health checks
- **Logging**: Structured JSON logging
- **Testing**: Comprehensive test scripts
- **Deployment**: Docker Compose with proper networking

### Known Issues (Resolved in Unreleased)
- UUID type mismatch errors in SQL queries
- JSON serialization issues for metadata
- Service startup sequence problems
- Database connection issues
- Environment variable loading problems
- Health check endpoint failures
- File permission issues
- Network connectivity problems

## [0.0.1] - 2024-07-15

### Added
- Initial project structure
- Basic architecture documentation
- Docker Compose setup for infrastructure services
- Core system design and planning
- Development environment setup

---

## Development Notes

### UUID Handling
All UUIDs in the system are stored as strings in the database and converted appropriately in application code. This ensures compatibility across different database drivers and prevents type mismatch errors.

### Database Schema
The database schema includes proper UUID extensions and JSON serialization for metadata fields. All tables use UUID primary keys with proper indexing.

### Service Communication
Services communicate over internal Docker networks with proper health checks and dependency management. The startup sequence ensures all dependencies are available before services start.

### Testing Strategy
The system includes multiple test scripts:
- `test_system.py`: Comprehensive system test
- `test_simple_upload.py`: Simple document upload test
- `test_upload_only.py`: Upload-only functionality test

### Monitoring and Observability
All services provide:
- Health check endpoints at `/health`
- Prometheus metrics at `/metrics`
- Structured JSON logging
- Error reporting and debugging information

### Security Considerations
- API keys are properly managed for external services
- Environment variables are securely loaded
- Service-to-service communication is isolated
- Audit logging is implemented for database operations

---

## Migration Guide

### From Previous Versions
If upgrading from a previous version:

1. **Backup your data**:
   ```bash
   docker-compose exec postgres pg_dump -U mep_user mep_ainabox > backup.sql
   ```

2. **Stop all services**:
   ```bash
   docker-compose down
   ```

3. **Update configuration**:
   - Copy new `env.example` to `.env`
   - Update any custom configurations

4. **Rebuild containers**:
   ```bash
   docker-compose build --no-cache
   ```

5. **Start services**:
   ```bash
   docker-compose up -d
   ```

6. **Verify installation**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   ```

7. **Run tests**:
   ```bash
   python test_simple_upload.py
   ```

### Breaking Changes
- UUID handling has been standardized across all services
- Database schema has been updated with proper UUID support
- Service startup sequence has been improved
- Environment variable loading has been enhanced

---

## Contributing

When contributing to this project, please:

1. Follow the established architecture patterns
2. Add comprehensive tests for new features
3. Update this changelog for any changes
4. Use structured logging and metrics
5. Follow security best practices
6. Test UUID handling for new database operations
7. Validate service health checks

---

## Support

For issues and questions:
1. Check the troubleshooting section in the README
2. Review logs and metrics
3. Check the architecture documentation
4. Create an issue with detailed information
5. Reference this changelog for recent changes 