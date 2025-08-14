#!/usr/bin/env python3
"""
Batch Process File Queue
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

def load_env_from_services():
    """Load environment variables from services/.env file"""
    try:
        # Try to find the services/.env file relative to this script
        script_dir = Path(__file__).parent
        services_env_path = script_dir.parent.parent / "services" / ".env"
        
        if services_env_path.exists():
            logger.info(f"📁 Loading environment variables from {services_env_path}")
            with open(services_env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        # Handle key=value format
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            
                            # Set environment variable if not already set
                            if key and value and key not in os.environ:
                                os.environ[key] = value
                                logger.debug(f"  Set {key}={value}")
            
            logger.info("✅ Environment variables loaded from services/.env")
        else:
            logger.warning(f"⚠️  Services .env file not found at {services_env_path}")
            
    except Exception as e:
        logger.error(f"❌ Error loading environment variables: {e}")

class BatchProcessFileQueue:
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
            
            # Do not use an items file; let the worker read directly from DB
            temp_file = None
            
            # Prefer Docker worker with bind mounts; fallback to direct only if docker.sock is unavailable
            if os.path.exists('/.dockerenv') and not os.path.exists('/var/run/docker.sock'):
                logger.info("🐳 Inside Docker without docker.sock, executing worker directly")
                return self.run_worker_direct(items, script_args)
            
            # Build Docker command
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "host"
            ]

            # Mount each folder group (normalize paths; do not require paths to exist inside this container)
            mount_points = []
            for folder_path in folder_groups.keys():
                if not folder_path:
                    continue
                normalized_path = os.path.normpath(folder_path)
                # Use the last segment of the normalized path; guard against empty names
                folder_name = os.path.basename(normalized_path) or "folder"
                mount_point = f"/mnt/{folder_name}"
                docker_cmd.extend(["-v", f"{normalized_path}:{mount_point}:ro"])
                mount_points.append(mount_point)
                logger.info(f"📁 Mounting folder: {normalized_path} -> {mount_point}")

                # Also mount the true parent directory (of the normalized path) if distinct
                parent_dir = os.path.dirname(normalized_path)
                if parent_dir and parent_dir != normalized_path:
                    parent_folder_name = os.path.basename(parent_dir) or "parent"
                    parent_mount = f"/mnt/parent_{parent_folder_name}"
                    docker_cmd.extend(["-v", f"{parent_dir}:{parent_mount}:ro"])
                    mount_points.append(parent_mount)
                    logger.info(f"📁 Mounting parent folder: {parent_dir} -> {parent_mount}")
            
            # No items file mount needed when worker reads from DB
            
            # Mount config into worker if available (works both when orchestrator runs in container or on host)
            host_core = os.getenv('DOCKER_HOST_CORE_PATH')
            logger.info(f"🔍 DOCKER_HOST_CORE_PATH: {host_core}")
            
            if host_core:
                # Mount host core config directly into worker (path validity is evaluated by Docker daemon)
                docker_cmd.extend(["-v", f"{host_core}/config:/app/config:ro"])
                # Also mount entire core so worker uses latest host code without rebuilding image
                docker_cmd.extend(["-v", f"{host_core}:/app"])
                # Mount services directory for .env file - use the host path that was passed to orchestrator
                services_path = Path(host_core).parent / "services"
                logger.info(f"🔍 Services path calculated: {services_path}")
                # Always mount the services directory using the calculated host path
                docker_cmd.extend(["-v", f"{str(services_path)}:/services:ro"])
                logger.info(f"📁 Mounting services directory: {services_path} -> /services")
            elif os.path.exists("/app/config"):
                logger.info("🔍 Using /app/config path")
                docker_cmd.extend(["-v", "/app/config:/app/config:ro"])
                # Mount services directory if available
                if os.path.exists("/app/../services"):
                    docker_cmd.extend(["-v", "/app/../services:/services:ro"])
                    logger.info("📁 Mounting services directory: /app/../services -> /services")
                else:
                    logger.warning("⚠️  Services directory not found at /app/../services")
            else:
                logger.info("🔍 Using fallback config path")
                host_config = Path(__file__).parent.parent / "config"
                if host_config.exists():
                    docker_cmd.extend(["-v", f"{str(host_config)}:/app/config:ro"])
                # Mount services directory for .env file
                services_path = Path(__file__).parent.parent / "services"
                logger.info(f"🔍 Services path calculated: {services_path}")
                # Always mount the services directory using the calculated host path
                docker_cmd.extend(["-v", f"{str(services_path)}:/services:ro"])
                logger.info(f"📁 Mounting services directory: {services_path} -> /services")

            # Add environment variables
            docker_cmd.extend([
                "-e", f"MOUNT_POINTS={','.join(mount_points)}"
            ])

            # Pass embedding/Qdrant/Ollama environment (fall back to localhost for host networking)
            env_defaults = {
                'EMBEDDING_PROVIDER': os.getenv('EMBEDDING_PROVIDER', 'huggingface'),
                'OLLAMA_HOST': os.getenv('OLLAMA_HOST', 'localhost'),
                'OLLAMA_PORT': os.getenv('OLLAMA_PORT', '11434'),
                'OLLAMA_DEFAULT_MODEL': os.getenv('OLLAMA_DEFAULT_MODEL', 'nomic-embed-text'),
                'QDRANT_HOST': os.getenv('QDRANT_HOST', 'localhost'),
                'QDRANT_PORT': os.getenv('QDRANT_PORT', '6333'),
                'QDRANT_COLLECTION': os.getenv('QDRANT_COLLECTION', 'documents'),
                'QDRANT_API_KEY': os.getenv('QDRANT_API_KEY', 'qdrant_api_key'),
                'HUGGINGFACE_HOST': os.getenv('HUGGINGFACE_HOST', 'localhost'),
                'HUGGINGFACE_PORT': os.getenv('HUGGINGFACE_PORT', '8082'),
                'HUGGINGFACE_MODEL': os.getenv('HUGGINGFACE_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                'EMBEDDING_PROCESSOR_URL': os.getenv('EMBEDDING_PROCESSOR_URL', 'http://localhost:8082/embed'),
                'EMBEDDING_CHUNK_SIZE': os.getenv('EMBEDDING_CHUNK_SIZE', '200'),
                'EMBEDDING_CHUNK_OVERLAP': os.getenv('EMBEDDING_CHUNK_OVERLAP', '20'),
                'EMBEDDING_BATCH_SIZE': os.getenv('EMBEDDING_BATCH_SIZE', '100')
            }
            # Log what we're passing (mask the API key)
            try:
                logger.info(
                    "🧩 Passing embedding env -> provider=%s, qdrant=%s:%s, collection=%s, ollama=%s:%s, model=%s, hf=%s:%s, hf_model=%s, api_key=%s",
                    env_defaults['EMBEDDING_PROVIDER'], env_defaults['QDRANT_HOST'], env_defaults['QDRANT_PORT'],
                    env_defaults['QDRANT_COLLECTION'], env_defaults['OLLAMA_HOST'], env_defaults['OLLAMA_PORT'],
                    env_defaults['OLLAMA_DEFAULT_MODEL'], env_defaults['HUGGINGFACE_HOST'], env_defaults['HUGGINGFACE_PORT'],
                    env_defaults['HUGGINGFACE_MODEL'], 'set' if env_defaults['QDRANT_API_KEY'] else 'not_set'
                )
            except Exception:
                pass
            for key, value in env_defaults.items():
                if key == 'QDRANT_API_KEY' and not value:
                    continue  # do not pass empty key
                docker_cmd.extend(["-e", f"{key}={value}"])
            
            # Add image and entrypoint
            docker_cmd.extend([
                "--entrypoint", "python3",
                self.docker_image,
                "/app/batch/process_file_processing_queue.py"
            ])
            
            # Add script arguments
            if script_args:
                docker_cmd.extend(script_args)
            else:
                # Add --no-stats by default to avoid the statistics printing issue
                docker_cmd.extend(["--no-stats"])
 
            logger.info(f"🚀 Running Docker command: {' '.join(docker_cmd)}")
            
            # Execute Docker command
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Log worker output preview for diagnostics
            try:
                if result.stdout:
                    logger.info("🧾 Worker stdout (preview): %s", (result.stdout[:4000] + ('…' if len(result.stdout) > 4000 else '')))
                if result.stderr:
                    logger.warning("⚠️  Worker stderr (preview): %s", (result.stderr[:4000] + ('…' if len(result.stderr) > 4000 else '')))
            except Exception:
                pass
            
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
            
            # Set up mount points for direct execution
            # When running inside Docker, we need to set up the mount points manually
            mount_points = []
            for item in items:
                parent_dir = item.get('parent_directory')
                if parent_dir and parent_dir not in mount_points:
                    mount_points.append(parent_dir)
            
            # Set the MOUNT_POINTS environment variable
            os.environ['MOUNT_POINTS'] = ','.join(mount_points)
            logger.info(f"🔧 Set mount points for direct execution: {mount_points}")

            # Ensure embedding/Qdrant/Ollama env are present (defaults suitable for --network host)
            os.environ.setdefault('EMBEDDING_PROVIDER', 'huggingface')
            os.environ.setdefault('OLLAMA_HOST', os.getenv('OLLAMA_HOST', 'localhost'))
            os.environ.setdefault('OLLAMA_PORT', os.getenv('OLLAMA_PORT', '11434'))
            os.environ.setdefault('OLLAMA_DEFAULT_MODEL', os.getenv('OLLAMA_DEFAULT_MODEL', 'nomic-embed-text'))
            os.environ.setdefault('QDRANT_HOST', os.getenv('QDRANT_HOST', 'localhost'))
            os.environ.setdefault('QDRANT_PORT', os.getenv('QDRANT_PORT', '6333'))
            os.environ.setdefault('QDRANT_COLLECTION', os.getenv('QDRANT_COLLECTION', 'documents'))
            os.environ.setdefault('HUGGINGFACE_HOST', os.getenv('HUGGINGFACE_HOST', 'localhost'))
            os.environ.setdefault('HUGGINGFACE_PORT', os.getenv('HUGGINGFACE_PORT', '8082'))
            os.environ.setdefault('HUGGINGFACE_MODEL', os.getenv('HUGGINGFACE_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'))
            os.environ.setdefault('EMBEDDING_PROCESSOR_URL', os.getenv('EMBEDDING_PROCESSOR_URL', 'http://localhost:8082/embed'))
            os.environ.setdefault('EMBEDDING_CHUNK_SIZE', os.getenv('EMBEDDING_CHUNK_SIZE', '200'))
            os.environ.setdefault('EMBEDDING_CHUNK_OVERLAP', os.getenv('EMBEDDING_CHUNK_OVERLAP', '20'))
            os.environ.setdefault('EMBEDDING_BATCH_SIZE', os.getenv('EMBEDDING_BATCH_SIZE', '100'))
            if os.getenv('QDRANT_API_KEY') and not os.environ.get('QDRANT_API_KEY'):
                os.environ['QDRANT_API_KEY'] = os.getenv('QDRANT_API_KEY')  # forward if set
            try:
                logger.info(
                    "🧩 Embedding env (direct) -> provider=%s, qdrant=%s:%s, collection=%s, ollama=%s:%s, model=%s, hf=%s:%s, hf_model=%s, api_key=%s",
                    os.environ.get('EMBEDDING_PROVIDER'), os.environ.get('QDRANT_HOST'), os.environ.get('QDRANT_PORT'),
                    os.environ.get('QDRANT_COLLECTION'), os.environ.get('OLLAMA_HOST'), os.environ.get('OLLAMA_PORT'),
                    os.environ.get('OLLAMA_DEFAULT_MODEL'), os.environ.get('HUGGINGFACE_HOST'), os.environ.get('HUGGINGFACE_PORT'),
                    os.environ.get('HUGGINGFACE_MODEL'), 'set' if os.environ.get('QDRANT_API_KEY') else 'not_set'
                )
            except Exception:
                pass
            
            # Build command to run the worker script
            cmd = ["python3", "/app/process_file_processing_queue.py"]
            
            # Add script arguments
            if script_args:
                cmd.extend(script_args)
            else:
                # Add --no-stats by default to avoid the statistics printing issue
                cmd.extend(["--no-stats"])
            
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
            
            # Let the worker update item statuses; do not change status here
            
            # Run worker in Docker
            logger.info("🚀 STARTING PROCESSING:")
            logger.info("=" * 60)
            result = self.run_worker_docker(items, script_args)
            
            if result['success']:
                logger.info("✅ PROCESSING COMPLETED (worker handled statuses)")
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
    parser = argparse.ArgumentParser(description="Batch process file queue for MEP AI NABOX")
    parser.add_argument("--processor-type", help="Only process items with this processor type")
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to process per batch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    # Accept all remaining args after --script-args (including options starting with '-')
    import argparse as _argparse  # alias to avoid confusion with top-level import
    parser.add_argument("--script-args", nargs=_argparse.REMAINDER, help="Additional arguments to pass to the worker script")
    
    # Parse known and unknown args so we can forward any extra flags to the worker
    args, unknown_args = parser.parse_known_args()
    
    # Load configuration
    config = load_config()
    
    # Load environment variables from services/.env
    load_env_from_services()
    
    # Initialize processor
    processor = BatchProcessFileQueue(config)
    
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
        
        # Determine worker script args from --script-args or any unknown args
        forward_args = args.script_args if args.script_args else []
        if unknown_args:
            # If user provided extra flags without --script-args, forward them
            forward_args = list(forward_args) + unknown_args

        # Process batch
        success = await processor.process_batch(
            processor_type=args.processor_type,
            limit=args.limit,
            script_args=forward_args
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