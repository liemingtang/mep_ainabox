# MEP AI NABOX - Admin Startup Guide

## Quick Start

### 1. Start All Services
```bash
./start_admin.sh
```

### 2. Stop All Services
```bash
./stop_admin.sh
```

### 3. Check Service Status
```bash
docker ps
```

## Available Scripts

### Core Management Scripts
- `start_admin.sh` - Start all MEP AI NABOX services
- `stop_admin.sh` - Stop all MEP AI NABOX services
- `scan_folder.sh` - Scan and process files from any folder
- `clean_all_data.sh` - Clean all database data (dry run by default)

### Monitoring and Recovery Scripts
- `fix_stuck_documents.py` - Detect and fix stuck documents
- `monitor_and_fix_stuck_documents.sh` - Automated monitoring script (cron-ready)
- `enhanced_monitor.py` - Advanced monitoring with queue and state management
- `queue_worker.py` - Dedicated queue worker for processing jobs

## Document Processing Modes

### 1. **Asynchronous Processing** (Default)
- **Endpoint**: `/process`
- **Speed**: Fast
- **Reliability**: Good (with retry logic)
- **Use Case**: Batch processing, non-critical documents

### 2. **Synchronous Processing** (Guaranteed)
- **Endpoint**: `/process-sync`
- **Speed**: Slower
- **Reliability**: **100% - No stuck documents possible**
- **Use Case**: Critical documents, production environments

### 3. **Queue-Based Processing** (Scalable)
- **Endpoint**: `/process-queue`
- **Speed**: Variable (depends on queue size)
- **Reliability**: **Excellent - Guaranteed message delivery**
- **Use Case**: High-volume processing, distributed systems

### 4. **Atomic Processing** (Database-Driven)
- **Endpoint**: `/process-atomic`
- **Speed**: Medium
- **Reliability**: **Perfect - Atomic database transactions**
- **Use Case**: Financial documents, audit trails

## Queue Management

### Queue Statistics
```bash
curl http://localhost:8003/queue/stats
```

### Clear Queues
```bash
curl -X POST http://localhost:8003/queue/clear
```

### Process Queue Worker
```bash
curl -X POST http://localhost:8003/process-queue-worker
```

### Run Dedicated Queue Worker
```bash
python3 queue_worker.py
```

## Enhanced Monitoring

### Single Analysis
```bash
# Dry run (recommended first)
python3 enhanced_monitor.py --dry-run

# Real execution
python3 enhanced_monitor.py
```

### Continuous Monitoring
```bash
# Monitor every 30 seconds
python3 enhanced_monitor.py --continuous --interval 30

# Monitor for 10 iterations
python3 enhanced_monitor.py --continuous --iterations 10
```

### Queue Statistics Only
```bash
python3 enhanced_monitor.py --queue-stats
```

### Cleanup Operations
```bash
# Clear all queues
python3 enhanced_monitor.py --clear-queues

# Clean up old jobs (older than 7 days)
python3 enhanced_monitor.py --cleanup 7
```

## Stuck Documents Prevention

### Root Causes Eliminated
1. **Distributed Status Management** → Centralized status management
2. **Asynchronous Fire-and-Forget** → Guaranteed message delivery
3. **Multiple Status Update Points** → Single atomic updates

### Prevention Methods
1. **Synchronous Processing**: Complete processing before returning
2. **Queue-Based Processing**: Guaranteed message delivery with Redis
3. **Atomic Database Updates**: Single transaction for all status changes
4. **Enhanced Retry Logic**: Exponential backoff with verification

### Monitoring and Recovery
1. **Real-time Monitoring**: Continuous queue and state monitoring
2. **Automatic Recovery**: Self-healing stuck documents
3. **Manual Intervention**: Tools for manual status correction
4. **Comprehensive Logging**: Detailed audit trails

## Service Health Checks

### Core Processor
```bash
curl http://localhost:8001/health
```

### Processing Pipeline
```bash
curl http://localhost:8003/health
```

### Text Processor
```bash
curl http://localhost:8004/health
```

### Embedding Processor
```bash
curl http://localhost:8005/health
```

## Database Management

### View Documents
```bash
curl http://localhost:8001/documents
```

### Get Document Status
```bash
curl http://localhost:8001/documents/{document_id}/processing-status
```

### Get Document State (Enhanced)
```bash
curl http://localhost:8003/state/{document_id}
```

### Get Stuck Documents (Enhanced)
```bash
curl http://localhost:8003/state/stuck-documents
```

## File Processing

### Scan Local Folder
```bash
./scan_folder.sh /path/to/folder
```

### Scan with Options
```bash
# Dry run
./scan_folder.sh /path/to/folder --dry-run

# Non-recursive
./scan_folder.sh /path/to/folder --no-recursive

# Max depth
./scan_folder.sh /path/to/folder --max-depth 3

# Concurrent processing
./scan_folder.sh /path/to/folder --concurrent 10

# Save report
./scan_folder.sh /path/to/folder --save-report my_report.json
```

## Troubleshooting

### Check Service Logs
```bash
# Core processor
docker logs mep-core-processor

# Processing pipeline
docker logs mep-processing-pipeline

# Text processor
docker logs mep-text-processor

# Embedding processor
docker logs mep-embedding-processor
```

### Restart Services
```bash
# Restart specific service
docker restart mep-processing-pipeline

# Restart all services
./stop_admin.sh && ./start_admin.sh
```

### Database Issues
```bash
# Check database connection
docker exec -it mep-postgres psql -U postgres -d mep_ainabox

# Reset database (WARNING: Deletes all data)
./clean_all_data.sh --real
```

### Queue Issues
```bash
# Check queue status
python3 enhanced_monitor.py --queue-stats

# Clear queues
python3 enhanced_monitor.py --clear-queues

# Restart queue worker
python3 queue_worker.py
```

## Performance Optimization

### Processing Modes by Use Case
- **Development/Testing**: Asynchronous processing
- **Production/Critical**: Synchronous processing
- **High Volume**: Queue-based processing
- **Audit Requirements**: Atomic processing

### Queue Worker Configuration
```bash
# Fast processing (1 second intervals)
python3 queue_worker.py --poll-interval 1.0

# Conservative processing (5 second intervals)
python3 queue_worker.py --poll-interval 5.0

# No statistics (reduced overhead)
python3 queue_worker.py --no-stats
```

### Monitoring Configuration
```bash
# Frequent monitoring (30 seconds)
python3 enhanced_monitor.py --continuous --interval 30

# Conservative monitoring (5 minutes)
python3 enhanced_monitor.py --continuous --interval 300
```

## Security Considerations

### File Access
- All file scanning uses read-only mounts
- No files are copied to processing containers
- Dynamic mounting for security isolation

### Database Access
- Environment variable-based authentication
- Atomic transactions prevent data corruption
- Comprehensive audit logging

### Network Security
- Internal Docker networking
- No external service dependencies
- Secure inter-service communication

## Backup and Recovery

### Database Backup
```bash
# PostgreSQL backup
docker exec mep-postgres pg_dump -U postgres mep_ainabox > backup.sql

# Restore
docker exec -i mep-postgres psql -U postgres mep_ainabox < backup.sql
```

### Configuration Backup
```bash
# Backup configuration
cp -r services/config backup_config/

# Restore configuration
cp -r backup_config/* services/config/
```

### Data Recovery
```bash
# Recover from stuck documents
python3 fix_stuck_documents.py --real

# Enhanced recovery
python3 enhanced_monitor.py --continuous --interval 60
```

## Advanced Configuration

### Environment Variables
```bash
# Core processor URL
export CORE_PROCESSOR_URL=http://localhost:8001

# Processing pipeline URL
export PROCESSING_PIPELINE_URL=http://localhost:8003

# Redis configuration
export REDIS_URL=redis://redis:6379
```

### Docker Compose Overrides
```bash
# Development overrides
docker compose -f core/docker-compose.yml -f core/docker-compose.dev.yml up

# Production overrides
docker compose -f core/docker-compose.yml -f core/docker-compose.prod.yml up
```

### Custom Processing Pipelines
```bash
# Add custom processors
# Edit core/processing_pipeline/main.py

# Rebuild and restart
docker compose -f core/docker-compose.yml build processing-pipeline
docker compose -f core/docker-compose.yml restart processing-pipeline
```

## Support and Maintenance

### Regular Maintenance
1. **Daily**: Check service health and logs
2. **Weekly**: Run enhanced monitoring and cleanup
3. **Monthly**: Review performance metrics and optimize
4. **Quarterly**: Update dependencies and security patches

### Emergency Procedures
1. **Service Down**: Restart with `./stop_admin.sh && ./start_admin.sh`
2. **Database Issues**: Use `clean_all_data.sh` (WARNING: Data loss)
3. **Stuck Documents**: Run `enhanced_monitor.py --continuous`
4. **Queue Issues**: Clear queues and restart worker

### Performance Monitoring
```bash
# Monitor queue performance
python3 enhanced_monitor.py --queue-stats

# Monitor processing performance
python3 queue_worker.py --stats-interval 30

# Monitor system resources
docker stats
```

This guide provides comprehensive management capabilities for the MEP AI NABOX system with multiple processing modes, enhanced monitoring, and robust recovery mechanisms. 