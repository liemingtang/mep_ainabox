#!/usr/bin/env python3
"""
Batch Processor Docker Container
Queries database for files and dynamically mounts folders for processing
"""

import argparse
import asyncio
import logging
import sys
import subprocess
import json
import tempfile
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

class BatchProcessorDocker:
    """Docker container for batch processing with dynamic folder mounting"""
    
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
    
    async def get_pending_items(self, processor_type: str = None, limit: int = 10) -> List[Dict]:
        """Get pending items from the queue with folder information"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT q.id, q.file_info_id, q.file_path, q.filename, q.priority, 
                           q.processor_type, q.metadata, q.retry_count, q.max_retries,
                           f.parent_directory
                    FROM file_processing_queue q
                    JOIN file_info f ON q.file_info_id = f.id
                    WHERE q.status = 'pending'
                """
                params = []
                
                if processor_type:
                    query += " AND q.processor_type = $1"
                    params.append(processor_type)
                
                query += " ORDER BY q.priority DESC, q.created_at ASC"
                
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
    
    def group_items_by_folder(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by their parent directory for efficient mounting"""
        folder_groups = {}
        
        for item in items:
            parent_dir = item.get('parent_directory', '')
            if parent_dir not in folder_groups:
                folder_groups[parent_dir] = []
            folder_groups[parent_dir].append(item)
        
        return folder_groups
    
    def run_worker_docker(self, items: List[Dict], script_args: List[str] = None) -> Dict[str, Any]:
        """Run the worker script in Docker with dynamic folder mounting"""
        try:
            # Group items by folder
            folder_groups = self.group_items_by_folder(items)
            
            # Create temporary file with items to process
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(items, f, indent=2)
                temp_file = f.name
            
            # Check if we're running inside Docker
            if os.path.exists('/.dockerenv'):
                # We're inside Docker, run the worker directly
                logger.info("🐳 Running inside Docker container, executing worker directly")
                return self.run_worker_direct(items, script_args)
            
            # Build Docker command
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "host"
            ]
            
            # Mount each folder group
            mount_points = []
            for folder_path in folder_groups.keys():
                if folder_path and os.path.exists(folder_path):
                    mount_point = f"/mnt/{os.path.basename(folder_path)}"
                    docker_cmd.extend(["-v", f"{folder_path}:{mount_point}:ro"])
                    mount_points.append(mount_point)
                    logger.info(f"📁 Mounting folder: {folder_path} -> {mount_point}")
            
            # Mount the temporary file with items
            docker_cmd.extend(["-v", f"{temp_file}:/app/items.json:ro"])
            
            # Add environment variables
            docker_cmd.extend([
                "-e", "ITEMS_FILE=/app/items.json",
                "-e", f"MOUNT_POINTS={','.join(mount_points)}"
            ])
            
            # Add image and command
            docker_cmd.extend([
                self.docker_image,
                "--entrypoint", "python3",
                "/app/process_queue_worker.py"
            ])
            
            # Add script arguments
            if script_args:
                docker_cmd.extend(script_args)
            
            logger.info(f"🚀 Running Docker command: {' '.join(docker_cmd)}")
            
            # Execute Docker command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Docker command timed out")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            logger.error(f"❌ Docker command failed: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def run_worker_direct(self, items: List[Dict], script_args: List[str] = None) -> Dict[str, Any]:
        """Run the worker script directly (when already inside Docker)"""
        try:
            # Set environment variables
            os.environ['ITEMS_FILE'] = '/app/items.json'
            
            # Create items file
            with open('/app/items.json', 'w') as f:
                json.dump(items, f, indent=2)
            
            # Build command to run the worker script
            cmd = ["python3", "/app/process_queue_worker.py"]
            
            # Add script arguments
            if script_args:
                cmd.extend(script_args)
            
            logger.info(f"🚀 Running worker directly: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Worker command timed out")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            logger.error(f"❌ Worker command failed: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    async def process_batch(self, processor_type: str = None, limit: int = 10, 
                           script_args: List[str] = None) -> bool:
        """Process a batch of items"""
        try:
            # Get pending items
            items = await self.get_pending_items(processor_type, limit)
            
            if not items:
                logger.info("ℹ️  No pending items to process")
                return True
            
            logger.info(f"📊 Found {len(items)} items to process")
            
            # Print detailed information about files to be processed
            logger.info("=" * 60)
            logger.info("📋 FILES TO BE PROCESSED:")
            logger.info("=" * 60)
            for i, item in enumerate(items, 1):
                logger.info(f"{i:2d}. 📄 {item['filename']}")
                logger.info(f"    📁 Path: {item['file_path']}")
                logger.info(f"    📂 Folder: {item.get('parent_directory', 'Unknown')}")
                logger.info(f"    ⚡ Priority: {item['priority']}")
                logger.info(f"    🔧 Processor: {item['processor_type']}")
                logger.info(f"    🆔 Queue ID: {item['id']}")
                logger.info(f"    📊 Status: pending")
                if item.get('metadata'):
                    logger.info(f"    📝 Metadata: {item['metadata']}")
                logger.info("")
            
            logger.info("=" * 60)
            
            # Update items to processing status and show status change
            logger.info("🔄 UPDATING STATUS TO PROCESSING:")
            logger.info("=" * 60)
            for item in items:
                logger.info(f"📄 {item['filename']} (ID: {item['id']}) - Status: pending → processing")
                await self.update_item_status(item['id'], 'processing')
            logger.info("=" * 60)
            
            # Run worker in Docker
            logger.info("🚀 STARTING PROCESSING:")
            logger.info("=" * 60)
            result = self.run_worker_docker(items, script_args)
            
            if result['success']:
                logger.info("✅ PROCESSING COMPLETED SUCCESSFULLY:")
                logger.info("=" * 60)
                # Update items to completed status and show final status
                for item in items:
                    logger.info(f"📄 {item['filename']} (ID: {item['id']}) - Status: processing → completed ✅")
                    await self.update_item_status(item['id'], 'completed')
                logger.info("=" * 60)
                return True
            else:
                logger.error("❌ PROCESSING FAILED:")
                logger.error("=" * 60)
                # Update items to failed status and show final status
                for item in items:
                    logger.error(f"📄 {item['filename']} (ID: {item['id']}) - Status: processing → failed ❌")
                    logger.error(f"    Error: {result['stderr']}")
                    await self.update_item_status(item['id'], 'failed', result['stderr'])
                logger.error("=" * 60)
                return False
                
        except Exception as e:
            logger.error(f"❌ Batch processing error: {e}")
            return False

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
    parser = argparse.ArgumentParser(description="Batch processor Docker container for MEP AI NABOX")
    parser.add_argument("--processor-type", help="Only process items with this processor type")
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to process per batch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    parser.add_argument("--script-args", nargs='*', help="Additional arguments to pass to the worker script")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize processor
    processor = BatchProcessorDocker(config)
    
    try:
        # Connect to database
        await processor.connect()
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No changes will be made")
            items = await processor.get_pending_items(args.processor_type, args.limit)
            
            if not items:
                logger.info("ℹ️  No pending items to process")
                return
            
            logger.info("=" * 60)
            logger.info("📋 ITEMS THAT WOULD BE PROCESSED:")
            logger.info("=" * 60)
            for i, item in enumerate(items, 1):
                logger.info(f"{i:2d}. 📄 {item['filename']}")
                logger.info(f"    📁 Path: {item['file_path']}")
                logger.info(f"    📂 Folder: {item.get('parent_directory', 'Unknown')}")
                logger.info(f"    ⚡ Priority: {item['priority']}")
                logger.info(f"    🔧 Processor: {item['processor_type']}")
                logger.info(f"    🆔 Queue ID: {item['id']}")
                logger.info(f"    📊 Status: pending")
                if item.get('metadata'):
                    logger.info(f"    📝 Metadata: {item['metadata']}")
                logger.info("")
            
            logger.info("=" * 60)
            return
        
        # Process batch
        success = await processor.process_batch(
            processor_type=args.processor_type,
            limit=args.limit,
            script_args=args.script_args
        )
        
        if not success:
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Batch processor failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        await processor.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 