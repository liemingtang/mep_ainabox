#!/usr/bin/env python3
"""
Queue File Processing Script
Reads files from file_info table and creates entries in file_processing_queue table
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import asyncpg
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
    
    async def connect(self):
        """Connect to PostgreSQL database"""
        try:
            postgres_config = self.config.get('core', {}).get('storage', {}).get('postgresql', {})
            
            self.pool = await asyncpg.create_pool(
                host=postgres_config.get('host', 'localhost'),
                port=postgres_config.get('port', 5432),
                database=postgres_config.get('database', 'mep_ainabox'),
                user=postgres_config.get('user', 'mep_user'),
                password=postgres_config.get('password', 'mep_password'),
                min_size=1,
                max_size=postgres_config.get('pool_size', 10)
            )
            
            logger.info("✅ Connected to PostgreSQL database")
            
            # Create tables if they don't exist
            await self.create_tables()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL database")
    
    async def create_tables(self):
        """Create necessary tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Create file_processing_queue table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS file_processing_queue (
                    id SERIAL PRIMARY KEY,
                    file_info_id INTEGER REFERENCES file_info(id) ON DELETE CASCADE,
                    file_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    processor_type TEXT DEFAULT 'default',
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_processing_queue_status ON file_processing_queue(status);
                CREATE INDEX IF NOT EXISTS idx_file_processing_queue_priority ON file_processing_queue(priority);
                CREATE INDEX IF NOT EXISTS idx_file_processing_queue_scheduled_at ON file_processing_queue(scheduled_at);
                CREATE INDEX IF NOT EXISTS idx_file_processing_queue_file_path ON file_processing_queue(file_path);
            """)
            
            logger.info("✅ Database tables created/verified")
    
    async def get_files_for_queuing(self, filters: Dict[str, Any] = None) -> List[Dict]:
        """Get files from file_info table based on filters"""
        try:
            async with self.pool.acquire() as conn:
                # Build query with filters
                query = """
                    SELECT id, file_path, filename, file_type, mime_type, 
                           file_size, checksum, is_directory, status
                    FROM file_info 
                    WHERE status = 'active'
                """
                params = []
                
                if filters:
                    if filters.get('file_type'):
                        query += " AND file_type = $1"
                        params.append(filters['file_type'])
                    
                    if filters.get('mime_type'):
                        query += f" AND mime_type LIKE ${len(params) + 1}"
                        params.append(f"%{filters['mime_type']}%")
                    
                    if filters.get('min_size'):
                        query += f" AND file_size >= ${len(params) + 1}"
                        params.append(filters['min_size'])
                    
                    if filters.get('max_size'):
                        query += f" AND file_size <= ${len(params) + 1}"
                        params.append(filters['max_size'])
                    
                    if filters.get('is_directory') is not None:
                        query += f" AND is_directory = ${len(params) + 1}"
                        params.append(filters['is_directory'])
                
                query += " ORDER BY scan_timestamp DESC"
                
                if filters and filters.get('limit'):
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(filters['limit'])
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get files for queuing: {e}")
            return []
    
    async def add_to_queue(self, file_info: Dict, priority: int = 5, 
                          processor_type: str = 'default', scheduled_at: datetime = None) -> bool:
        """Add a file to the processing queue"""
        try:
            async with self.pool.acquire() as conn:
                # Check if file is already in queue
                existing = await conn.fetchrow("""
                    SELECT id FROM file_processing_queue 
                    WHERE file_info_id = $1 AND status IN ('pending', 'processing')
                """, file_info['id'])
                
                if existing:
                    logger.info(f"⚠️  File already in queue: {file_info['filename']}")
                    return False
                
                # Add to queue
                metadata = {
                    'file_type': file_info['file_type'], 
                    'mime_type': file_info['mime_type'],
                    'file_size': file_info['file_size'], 
                    'is_directory': file_info['is_directory']
                }
                
                await conn.execute("""
                    INSERT INTO file_processing_queue (
                        file_info_id, file_path, filename, priority, 
                        processor_type, scheduled_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, file_info['id'], file_info['file_path'], file_info['filename'],
                priority, processor_type, scheduled_at or datetime.now(),
                json.dumps(metadata))
                
                logger.info(f"✅ Added to queue: {file_info['filename']} (priority: {priority})")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to add file to queue: {e}")
            return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
                    FROM file_processing_queue
                """)
                
                return dict(stats) if stats else {}
                
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {}

def load_config() -> Dict[str, Any]:
    """Load configuration from main.yaml"""
    try:
        # Try Docker path first (when running in container)
        config_path = Path("/app/config/main.yaml")
        if not config_path.exists():
            # Fall back to relative path (when running locally)
            config_path = Path(__file__).parent.parent / "config" / "main.yaml"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning("Configuration file not found, using defaults")
            return {}
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Queue file processing for MEP AI NABOX")
    parser.add_argument("--file-type", help="Filter by file type (e.g., '.pdf', '.txt')")
    parser.add_argument("--mime-type", help="Filter by MIME type (e.g., 'application/pdf')")
    parser.add_argument("--min-size", type=int, help="Minimum file size in bytes")
    parser.add_argument("--max-size", type=int, help="Maximum file size in bytes")
    parser.add_argument("--files-only", action="store_true", help="Only process files (exclude directories)")
    parser.add_argument("--directories-only", action="store_true", help="Only process directories")
    parser.add_argument("--priority", type=int, default=5, help="Priority for queued items (1-10, default: 5)")
    parser.add_argument("--processor-type", default="default", help="Processor type for the queue")
    parser.add_argument("--limit", type=int, help="Maximum number of files to queue")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--stats", action="store_true", help="Show queue statistics")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    try:
        # Connect to database
        await db_manager.connect()
        
        if args.stats:
            # Show queue statistics
            stats = await db_manager.get_queue_stats()
            logger.info("=" * 50)
            logger.info("QUEUE STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Total items: {stats.get('total', 0)}")
            logger.info(f"Pending: {stats.get('pending', 0)}")
            logger.info(f"Processing: {stats.get('processing', 0)}")
            logger.info(f"Completed: {stats.get('completed', 0)}")
            logger.info(f"Failed: {stats.get('failed', 0)}")
            logger.info(f"Cancelled: {stats.get('cancelled', 0)}")
            logger.info("=" * 50)
            return
        
        # Build filters
        filters = {}
        if args.file_type:
            filters['file_type'] = args.file_type
        if args.mime_type:
            filters['mime_type'] = args.mime_type
        if args.min_size:
            filters['min_size'] = args.min_size
        if args.max_size:
            filters['max_size'] = args.max_size
        if args.files_only:
            filters['is_directory'] = False
        if args.directories_only:
            filters['is_directory'] = True
        if args.limit:
            filters['limit'] = args.limit
        
        # Get files for queuing
        logger.info("🔍 Finding files to queue...")
        files = await db_manager.get_files_for_queuing(filters)
        
        if not files:
            logger.info("ℹ️  No files found matching the criteria")
            return
        
        logger.info(f"📊 Found {len(files)} files to queue")
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            logger.info("=" * 50)
            logger.info("FILES THAT WOULD BE QUEUED:")
            logger.info("=" * 50)
            for file_info in files:
                logger.info(f"  - {file_info['filename']} ({file_info['file_path']})")
            logger.info("=" * 50)
            return
        
        # Add files to queue
        logger.info(f"🚀 Adding files to queue with priority {args.priority}...")
        queued_count = 0
        
        for file_info in files:
            success = await db_manager.add_to_queue(
                file_info, 
                priority=args.priority,
                processor_type=args.processor_type
            )
            if success:
                queued_count += 1
        
        # Show results
        logger.info("=" * 50)
        logger.info("QUEUE RESULTS")
        logger.info("=" * 50)
        logger.info(f"Files processed: {len(files)}")
        logger.info(f"Successfully queued: {queued_count}")
        logger.info(f"Already in queue: {len(files) - queued_count}")
        logger.info(f"Priority: {args.priority}")
        logger.info(f"Processor type: {args.processor_type}")
        logger.info("=" * 50)
        
        # Show updated stats
        stats = await db_manager.get_queue_stats()
        logger.info(f"📊 Queue statistics: {stats.get('pending', 0)} pending, {stats.get('processing', 0)} processing")
    
    except Exception as e:
        logger.error(f"❌ Queue processing failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 