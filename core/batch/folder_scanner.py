#!/usr/bin/env python3
"""
Batch Folder Scanner
Scans a folder and stores file information in PostgreSQL database
"""

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import asyncpg
from dataclasses import dataclass
import mimetypes
import magic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """File information data class"""
    file_path: str
    filename: str
    file_size: int
    file_type: str
    mime_type: str
    checksum: str
    created_time: datetime
    modified_time: datetime
    accessed_time: datetime
    is_directory: bool
    parent_directory: str
    depth: int
    permissions: str
    owner: str
    group_name: str

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
            # Create file_info table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS file_info (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    file_type TEXT,
                    mime_type TEXT,
                    checksum TEXT NOT NULL,
                    created_time TIMESTAMP,
                    modified_time TIMESTAMP NOT NULL,
                    accessed_time TIMESTAMP,
                    is_directory BOOLEAN DEFAULT FALSE,
                    parent_directory TEXT,
                    depth INTEGER DEFAULT 0,
                    permissions TEXT,
                    owner TEXT,
                    group_name TEXT,
                    scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create scan_sessions table to track scanning sessions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    folder_path TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    total_files INTEGER DEFAULT 0,
                    processed_files INTEGER DEFAULT 0,
                    failed_files INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Create indexes for better performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_info_path ON file_info(file_path);
                CREATE INDEX IF NOT EXISTS idx_file_info_checksum ON file_info(checksum);
                CREATE INDEX IF NOT EXISTS idx_file_info_modified ON file_info(modified_time);
                CREATE INDEX IF NOT EXISTS idx_file_info_parent ON file_info(parent_directory);
                CREATE INDEX IF NOT EXISTS idx_file_info_status ON file_info(status);
            """)
            
            logger.info("✅ Database tables created/verified")
    
    async def insert_or_update_file(self, file_info: FileInfo, session_id: str, force: bool = False) -> bool:
        """Insert or update file information in database"""
        try:
            async with self.pool.acquire() as conn:
                # Check if file exists
                existing = await conn.fetchrow("""
                    SELECT checksum, modified_time FROM file_info 
                    WHERE file_path = $1
                """, file_info.file_path)
                
                if existing:
                    # File exists, check if it has changed or if force is enabled
                    if force or existing['checksum'] != file_info.checksum:
                        # File has changed or force is enabled, update it
                        await conn.execute("""
                            UPDATE file_info SET
                                file_size = $2,
                                file_type = $3,
                                mime_type = $4,
                                checksum = $5,
                                modified_time = $6,
                                accessed_time = $7,
                                permissions = $8,
                                owner = $9,
                                group_name = $10,
                                last_checked = CURRENT_TIMESTAMP,
                                metadata = $11
                            WHERE file_path = $1
                        """, file_info.file_path, file_info.file_size, file_info.file_type,
                        file_info.mime_type, file_info.checksum, file_info.modified_time,
                        file_info.accessed_time, file_info.permissions, file_info.owner,
                        file_info.group_name, '{}')
                        
                        if force:
                            logger.info(f"🔄 Force updated file: {file_info.filename}")
                        else:
                            logger.info(f"🔄 Updated file: {file_info.filename}")
                        return True
                    else:
                        # File hasn't changed, just update last_checked
                        await conn.execute("""
                            UPDATE file_info SET last_checked = CURRENT_TIMESTAMP
                            WHERE file_path = $1
                        """, file_info.file_path)
                        return False
                else:
                    # New file, insert it
                    await conn.execute("""
                        INSERT INTO file_info (
                            file_path, filename, file_size, file_type, mime_type,
                            checksum, created_time, modified_time, accessed_time,
                            is_directory, parent_directory, depth, permissions,
                            owner, group_name, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    """, file_info.file_path, file_info.filename, file_info.file_size,
                    file_info.file_type, file_info.mime_type, file_info.checksum,
                    file_info.created_time, file_info.modified_time, file_info.accessed_time,
                    file_info.is_directory, file_info.parent_directory, file_info.depth,
                    file_info.permissions, file_info.owner, file_info.group_name, '{}')
                    
                    logger.info(f"✅ Added new file: {file_info.filename}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to insert/update file {file_info.file_path}: {e}")
            return False
    
    async def create_scan_session(self, session_id: str, folder_path: str) -> bool:
        """Create a new scan session"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scan_sessions (session_id, folder_path, status)
                    VALUES ($1, $2, 'running')
                """, session_id, folder_path)
                logger.info(f"✅ Created scan session: {session_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create scan session: {e}")
            return False
    
    async def update_scan_session(self, session_id: str, status: str, 
                                processed: int = 0, failed: int = 0, total: int = 0):
        """Update scan session status"""
        try:
            async with self.pool.acquire() as conn:
                if status == 'completed':
                    await conn.execute("""
                        UPDATE scan_sessions SET
                            status = $2,
                            completed_at = CURRENT_TIMESTAMP,
                            processed_files = $3,
                            failed_files = $4,
                            total_files = $5
                        WHERE session_id = $1
                    """, session_id, status, processed, failed, total)
                else:
                    await conn.execute("""
                        UPDATE scan_sessions SET
                            status = $2,
                            processed_files = $3,
                            failed_files = $4,
                            total_files = $5
                        WHERE session_id = $1
                    """, session_id, status, processed, failed, total)
        except Exception as e:
            logger.error(f"❌ Failed to update scan session: {e}")

class FolderScanner:
    """Scans folders and extracts file information"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.host_folder_path = os.environ.get('HOST_FOLDER_PATH', '')
    
    def convert_to_host_path(self, container_path: str) -> str:
        """Convert container path to host path"""
        if not self.host_folder_path:
            return container_path
        
        # If the path starts with /scan, replace it with the host folder path
        if container_path.startswith('/scan'):
            relative_path = container_path[5:]  # Remove '/scan'
            if relative_path.startswith('/'):
                relative_path = relative_path[1:]  # Remove leading slash
            return os.path.join(self.host_folder_path, relative_path)
        
        return container_path
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_path: Path, depth: int = 0) -> Optional[FileInfo]:
        """Extract file information"""
        try:
            stat = file_path.stat()
            
            # Get file type and mime type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                # Try using python-magic for better detection
                try:
                    mime_type = magic.from_file(str(file_path), mime=True)
                except:
                    mime_type = "application/octet-stream"
            
            file_type = file_path.suffix.lower() if file_path.suffix else "unknown"
            
            # Calculate checksum (only for files, not directories)
            checksum = ""
            if file_path.is_file():
                checksum = self.calculate_checksum(str(file_path))
            
            # Get file permissions
            permissions = oct(stat.st_mode)[-3:]
            
            # Get owner and group (platform dependent)
            try:
                import pwd
                import grp
                owner = pwd.getpwuid(stat.st_uid).pw_name
                group = grp.getgrgid(stat.st_gid).gr_name
            except:
                owner = str(stat.st_uid)
                group = str(stat.st_gid)
            
            # Convert container path to host path
            host_file_path = self.convert_to_host_path(str(file_path.absolute()))
            host_parent_path = self.convert_to_host_path(str(file_path.parent))
            
            return FileInfo(
                file_path=host_file_path,
                filename=file_path.name,
                file_size=stat.st_size,
                file_type=file_type,
                mime_type=mime_type or "application/octet-stream",
                checksum=checksum,
                created_time=datetime.fromtimestamp(stat.st_ctime),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                accessed_time=datetime.fromtimestamp(stat.st_atime),
                is_directory=file_path.is_dir(),
                parent_directory=host_parent_path,
                depth=depth,
                permissions=permissions,
                owner=owner,
                group_name=group
            )
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
    
    async def scan_folder(self, folder_path: str, session_id: str, 
                         max_depth: Optional[int] = None, force: bool = False) -> Dict[str, int]:
        """Scan folder and store file information in database"""
        folder = Path(folder_path)
        
        if not folder.exists():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")
        
        if not folder.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        
        logger.info(f"🔍 Starting scan of folder: {folder_path}")
        
        # Create scan session
        await self.db_manager.create_scan_session(session_id, folder_path)
        
        processed = 0
        failed = 0
        total = 0
        
        try:
            # Walk through the directory tree
            for root, dirs, files in os.walk(folder_path):
                current_depth = root.replace(str(folder), '').count(os.sep)
                
                # Check max depth
                if max_depth is not None and current_depth > max_depth:
                    continue
                
                # Process directories
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    file_info = self.get_file_info(dir_path, current_depth)
                    
                    if file_info:
                        total += 1
                        success = await self.db_manager.insert_or_update_file(file_info, session_id, force)
                        if success:
                            processed += 1
                        else:
                            # File exists but hasn't changed - still count as processed
                            processed += 1
                
                # Process files
                for file_name in files:
                    file_path = Path(root) / file_name
                    file_info = self.get_file_info(file_path, current_depth)
                    
                    if file_info:
                        total += 1
                        success = await self.db_manager.insert_or_update_file(file_info, session_id, force)
                        if success:
                            processed += 1
                        else:
                            # File exists but hasn't changed - still count as processed
                            processed += 1
                    
                    # Update session progress every 100 files
                    if total % 100 == 0:
                        await self.db_manager.update_scan_session(
                            session_id, "running", processed, failed, total
                        )
            
            # Final session update
            await self.db_manager.update_scan_session(
                session_id, "completed", processed, failed, total
            )
            
            logger.info(f"✅ Scan completed: {processed} processed, {failed} failed, {total} total")
            
            return {
                "processed": processed,
                "failed": failed,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"❌ Scan failed: {e}")
            await self.db_manager.update_scan_session(
                session_id, "failed", processed, failed, total
            )
            raise

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
    parser = argparse.ArgumentParser(description="Batch folder scanner for MEP AI NABOX")
    parser.add_argument("folder_path", help="Path to the folder to scan")
    parser.add_argument("--max-depth", type=int, help="Maximum depth to scan (default: unlimited)")
    parser.add_argument("--session-id", help="Custom session ID (default: auto-generated)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true", help="Force scan all files regardless of changes")
    
    args = parser.parse_args()
    
    # Validate folder path
    if not os.path.exists(args.folder_path):
        logger.error(f"Folder does not exist: {args.folder_path}")
        sys.exit(1)
    
    if not os.path.isdir(args.folder_path):
        logger.error(f"Path is not a directory: {args.folder_path}")
        sys.exit(1)
    
    # Load configuration
    config = load_config()
    
    # Generate session ID if not provided
    session_id = args.session_id or f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    try:
        # Connect to database
        await db_manager.connect()
        
        # Initialize scanner
        scanner = FolderScanner(db_manager)
        
        # Start scanning
        logger.info(f"🚀 Starting batch scan of: {args.folder_path}")
        logger.info(f"📊 Session ID: {session_id}")
        logger.info(f"📁 Max depth: {args.max_depth or 'unlimited'}")
        if args.force:
            logger.info(f"🔧 Force mode enabled - will update all files regardless of changes")
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            # In dry run mode, just count files
            total_files = 0
            for root, dirs, files in os.walk(args.folder_path):
                total_files += len(files) + len(dirs)
            logger.info(f"📊 Would process {total_files} files/directories")
        else:
            # Perform actual scan
            result = await scanner.scan_folder(args.folder_path, session_id, args.max_depth, args.force)
            
            logger.info("=" * 50)
            logger.info("SCAN RESULTS")
            logger.info("=" * 50)
            logger.info(f"Total files/directories: {result['total']}")
            logger.info(f"Successfully processed: {result['processed']}")
            logger.info(f"Failed: {result['failed']}")
            logger.info(f"Session ID: {session_id}")
            logger.info("=" * 50)
    
    except Exception as e:
        logger.error(f"❌ Scan failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 