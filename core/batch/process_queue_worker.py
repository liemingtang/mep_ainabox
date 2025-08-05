#!/usr/bin/env python3
"""
Queue Processing Worker
Processes files from file_processing_queue table using text_processor.py
"""

import argparse
import asyncio
import logging
import sys
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QueueWorker:
    """Worker for processing files from the queue"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        self.docker_image = "mep-folder-scanner:latest"
    
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
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL database")
    
    def get_items_from_file(self) -> List[Dict]:
        """Get items from JSON file (when running in Docker container)"""
        try:
            items_file = os.environ.get('ITEMS_FILE', '/app/items.json')
            if os.path.exists(items_file):
                with open(items_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Items file not found: {items_file}")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to load items from file: {e}")
            return []
    
    async def get_pending_items(self, processor_type: str = None, limit: int = 10) -> List[Dict]:
        """Get pending items from the queue or from file"""
        # Check if we're running in Docker container with items file
        if os.environ.get('ITEMS_FILE'):
            return self.get_items_from_file()
        
        # Otherwise, query the database
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT id, file_info_id, file_path, filename, priority, 
                           processor_type, metadata, retry_count, max_retries
                    FROM file_processing_queue 
                    WHERE status = 'pending'
                """
                params = []
                
                if processor_type:
                    query += " AND processor_type = $1"
                    params.append(processor_type)
                
                query += " ORDER BY priority DESC, created_at ASC"
                
                if limit:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to get pending items: {e}")
            return []
    
    async def update_item_status(self, item_id: int, status: str, error_message: str = None, 
                                started_at: datetime = None, completed_at: datetime = None):
        """Update queue item status"""
        try:
            async with self.pool.acquire() as conn:
                if status == 'processing':
                    await conn.execute("""
                        UPDATE file_processing_queue SET
                            status = $2,
                            started_at = $3
                        WHERE id = $1
                    """, item_id, status, started_at or datetime.now())
                elif status == 'completed':
                    await conn.execute("""
                        UPDATE file_processing_queue SET
                            status = $2,
                            completed_at = $3
                        WHERE id = $1
                    """, item_id, status, completed_at or datetime.now())
                elif status == 'failed':
                    await conn.execute("""
                        UPDATE file_processing_queue SET
                            status = $2,
                            error_message = $3,
                            retry_count = retry_count + 1
                        WHERE id = $1
                    """, item_id, status, error_message)
                
                logger.info(f"🔄 Updated item {item_id} status to: {status}")
                
        except Exception as e:
            logger.error(f"❌ Failed to update item status: {e}")
    
    def run_text_processor_docker(self, file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """Run text_processor.py via Docker"""
        try:
            # Build Docker command
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "host",
                "-v", f"{file_path}:{file_path}:ro"
            ]
            
            # Add output directory if specified
            if output_dir:
                docker_cmd.extend(["-v", f"{output_dir}:{output_dir}"])
            
            # Add environment variables
            docker_cmd.extend([
                "-e", f"INPUT_FILE={file_path}",
                "-e", f"OUTPUT_DIR={output_dir or '/tmp'}"
            ])
            
            # Add image and command
            docker_cmd.extend([
                self.docker_image,
                "--entrypoint", "python3",
                "/app/text_processor.py",
                file_path
            ])
            
            if output_dir:
                docker_cmd.extend(["--output-dir", output_dir])
            
            logger.info(f"🚀 Running Docker command: {' '.join(docker_cmd)}")
            
            # Execute Docker command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Docker command timed out for {file_path}")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            logger.error(f"❌ Docker command failed for {file_path}: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def find_file_in_mounted_folders(self, filename: str, parent_directory: str) -> str:
        """Find file in mounted folders"""
        try:
            # Get mount points from environment
            mount_points = os.environ.get('MOUNT_POINTS', '').split(',')
            
            # Try to find the file in mounted folders
            for mount_point in mount_points:
                if mount_point:
                    # Look for the file in the mount point
                    potential_path = os.path.join(mount_point, filename)
                    if os.path.exists(potential_path):
                        logger.info(f"📁 Found file in mount point: {potential_path}")
                        return potential_path
            
            # If not found in mount points, try the original path
            if os.path.exists(parent_directory):
                potential_path = os.path.join(parent_directory, filename)
                if os.path.exists(potential_path):
                    logger.info(f"📁 Found file in original path: {potential_path}")
                    return potential_path
            
            logger.warning(f"⚠️  File {filename} not found in any mounted folders")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding file {filename}: {e}")
            return None
    
    async def process_item(self, item: Dict) -> bool:
        """Process a single queue item"""
        item_id = item['id']
        file_path = item['file_path']
        filename = item['filename']
        parent_directory = item.get('parent_directory', '')
        retry_count = item['retry_count']
        max_retries = item['max_retries']
        
        logger.info(f"🔄 Processing item {item_id}: {filename}")
        
        # Find the actual file path in mounted folders
        actual_file_path = self.find_file_in_mounted_folders(filename, parent_directory)
        
        if not actual_file_path:
            error_msg = f"File not found: {filename} in any mounted folders"
            await self.update_item_status(item_id, 'failed', error_msg)
            return False
        
        # Update status to processing
        await self.update_item_status(item_id, 'processing')
        
        # Determine output directory
        output_dir = None
        if item.get('metadata'):
            try:
                metadata = json.loads(item['metadata']) if isinstance(item['metadata'], str) else item['metadata']
                # You can add logic here to determine output directory based on metadata
                output_dir = f"/tmp/processed/{filename}"
            except:
                pass
        
        # Run text processor
        result = self.run_text_processor_docker(actual_file_path, output_dir)
        
        if result['success']:
            logger.info(f"✅ Successfully processed {filename}")
            await self.update_item_status(item_id, 'completed')
            return True
        else:
            error_msg = f"Processing failed: {result['stderr']}"
            logger.error(f"❌ Failed to process {filename}: {error_msg}")
            
            # Check if we should retry
            if retry_count < max_retries:
                logger.info(f"🔄 Retrying {filename} (attempt {retry_count + 1}/{max_retries})")
                await self.update_item_status(item_id, 'failed', error_msg)
                return False
            else:
                logger.error(f"❌ Max retries exceeded for {filename}")
                await self.update_item_status(item_id, 'failed', error_msg)
                return False
    
    async def run_worker(self, processor_type: str = None, limit: int = 10, 
                        continuous: bool = False, interval: int = 30):
        """Run the worker loop"""
        logger.info(f"🚀 Starting queue worker (processor_type: {processor_type}, limit: {limit})")
        
        while True:
            try:
                # Get pending items
                items = await self.get_pending_items(processor_type, limit)
                
                if not items:
                    if continuous:
                        logger.info(f"⏳ No pending items, waiting {interval} seconds...")
                        await asyncio.sleep(interval)
                        continue
                    else:
                        logger.info("ℹ️  No pending items to process")
                        break
                
                logger.info(f"📊 Found {len(items)} items to process")
                
                # Process items
                processed_count = 0
                failed_count = 0
                
                for item in items:
                    success = await self.process_item(item)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                
                logger.info(f"✅ Processed {processed_count} items, {failed_count} failed")
                
                if not continuous:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                if not continuous:
                    break
                await asyncio.sleep(interval)

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
    parser = argparse.ArgumentParser(description="Queue processing worker for MEP AI NABOX")
    parser.add_argument("--processor-type", help="Only process items with this processor type")
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to process per batch")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Interval between batches in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize worker
    worker = QueueWorker(config)
    
    try:
        # Connect to database
        await worker.connect()
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            items = await worker.get_pending_items(args.processor_type, args.limit)
            logger.info("=" * 50)
            logger.info("ITEMS THAT WOULD BE PROCESSED:")
            logger.info("=" * 50)
            for item in items:
                logger.info(f"  - {item['filename']} ({item['file_path']}) - Priority: {item['priority']}")
            logger.info("=" * 50)
            return
        
        # Run worker
        await worker.run_worker(
            processor_type=args.processor_type,
            limit=args.limit,
            continuous=args.continuous,
            interval=args.interval
        )
    
    except Exception as e:
        logger.error(f"❌ Worker failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        await worker.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 