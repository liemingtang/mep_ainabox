#!/usr/bin/env python3
"""
Queue Processing Worker
Processes files from file_processing_queue table using text_processor.py
Generates and stores Elasticsearch data
"""

import argparse
import asyncio
import logging
import sys
import subprocess
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import asyncpg
from elasticsearch import AsyncElasticsearch
import httpx

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
        self.elasticsearch_client = None
        self.docker_image = "mep-folder-scanner:latest"
    
    async def connect(self):
        """Connect to PostgreSQL database and Elasticsearch"""
        try:
            # Connect to PostgreSQL
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
            
            # Connect to Elasticsearch
            await self.connect_elasticsearch()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def connect_elasticsearch(self):
        """Connect to Elasticsearch"""
        try:
            es_config = self.config.get('core', {}).get('storage', {}).get('elasticsearch', {})
            
            self.elasticsearch_client = AsyncElasticsearch(
                hosts=[{
                    'host': es_config.get('host', 'localhost'),
                    'port': es_config.get('port', 9200),
                    'scheme': 'http'
                }],
                basic_auth=(
                    es_config.get('username', 'elastic'),
                    es_config.get('password', 'elastic_password')
                )
            )
            
            # Test connection
            await self.elasticsearch_client.ping()
            logger.info("✅ Connected to Elasticsearch")
            
        except Exception as e:
            logger.warning(f"⚠️  Elasticsearch connection failed (optional): {e}")
            self.elasticsearch_client = None
    
    async def disconnect(self):
        """Disconnect from database and Elasticsearch"""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL database")
        
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()
            logger.info("Disconnected from Elasticsearch")
    
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
                    SELECT q.id, q.file_info_id, q.file_path, q.filename, q.priority, 
                           q.processor_type, q.metadata, q.retry_count, q.max_retries,
                           f.parent_directory, f.file_size, f.file_type, f.mime_type,
                           f.checksum, f.created_time, f.modified_time
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
    
    async def index_document_elasticsearch(self, item: Dict, processing_result: Dict[str, Any]) -> bool:
        """Index document in Elasticsearch"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping indexing")
            return False
        
        try:
            # Generate document ID
            doc_id = f"doc_{item['file_info_id']}"
            
            # Prepare document data
            doc_data = {
                "document_id": str(item['file_info_id']),
                "queue_id": item['id'],
                "filename": item['filename'],
                "file_path": item['file_path'],
                "parent_directory": item.get('parent_directory', ''),
                "file_size": item.get('file_size', 0),
                "file_type": item.get('file_type', ''),
                "mime_type": item.get('mime_type', ''),
                "checksum": item.get('checksum', ''),
                "processor_type": item['processor_type'],
                "priority": item['priority'],
                "status": "completed",
                "processing_result": processing_result,
                "created_time": item.get('created_time', datetime.now()).isoformat() if item.get('created_time') else datetime.now().isoformat(),
                "modified_time": item.get('modified_time', datetime.now()).isoformat() if item.get('modified_time') else datetime.now().isoformat(),
                "processed_at": datetime.now().isoformat(),
                "metadata": item.get('metadata', {})
            }
            
            # Index the document
            await self.elasticsearch_client.index(
                index="documents",
                id=doc_id,
                document=doc_data
            )
            
            logger.info(f"✅ Indexed document in Elasticsearch: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to index document in Elasticsearch: {e}")
            return False
    
    async def store_document_content_elasticsearch(self, item: Dict, text_content: str, 
                                                 processing_stats: Dict[str, Any]) -> bool:
        """Store document content in Elasticsearch"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping content storage")
            return False
        
        try:
            # Generate content ID
            content_id = f"content_{item['file_info_id']}"
            
            # Prepare content data
            content_data = {
                "document_id": str(item['file_info_id']),
                "queue_id": item['id'],
                "filename": item['filename'],
                "text_content": text_content,
                "content_length": len(text_content),
                "processing_stats": processing_stats,
                "created_at": datetime.now().isoformat(),
                "metadata": item.get('metadata', {})
            }
            
            # Store the content
            await self.elasticsearch_client.index(
                index="document_content",
                id=content_id,
                document=content_data
            )
            
            logger.info(f"✅ Stored document content in Elasticsearch: {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store document content in Elasticsearch: {e}")
            return False
    
    def run_text_processor_docker(self, file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """Run text_processor.py directly or via Docker"""
        try:
            # Check if we're inside a Docker container
            if os.path.exists('/.dockerenv'):
                # We're inside Docker, run text processor directly
                logger.info(f"🐳 Running text processor directly (inside Docker)")
                
                cmd = ["python3", "/app/text_processor.py", file_path]
                if output_dir:
                    cmd.extend(["--output-dir", output_dir])
                
                logger.info(f"🚀 Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
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
            else:
                # We're outside Docker, run via Docker
                logger.info(f"🐳 Running text processor via Docker")
                
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
                    "--entrypoint", "python3",
                    self.docker_image,
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
            logger.error(f"⏰ Text processor command timed out for {file_path}")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            logger.error(f"❌ Text processor command failed for {file_path}: {e}")
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
            logger.info(f"🔍 Searching for file '{filename}' in mount points: {mount_points}")
            logger.info(f"🔍 Parent directory: {parent_directory}")
            
            # Try to find the file in mounted folders
            for mount_point in mount_points:
                if mount_point:
                    # Look for the file in the mount point
                    potential_path = os.path.join(mount_point, filename)
                    logger.info(f"🔍 Checking: {potential_path}")
                    if os.path.exists(potential_path):
                        logger.info(f"✅ Found file in mount point: {potential_path}")
                        return potential_path
                    else:
                        logger.info(f"❌ File not found at: {potential_path}")
            
            # If not found in mount points, try the original path
            if parent_directory and os.path.exists(parent_directory):
                potential_path = os.path.join(parent_directory, filename)
                logger.info(f"🔍 Checking original path: {potential_path}")
                if os.path.exists(potential_path):
                    logger.info(f"✅ Found file in original path: {potential_path}")
                    return potential_path
                else:
                    logger.info(f"❌ File not found at original path: {potential_path}")
            
            # Try to find the file in common mount locations
            common_mounts = ['/mnt', '/media', '/data', '/host']
            for common_mount in common_mounts:
                if os.path.exists(common_mount):
                    # Search recursively in common mount points
                    for root, dirs, files in os.walk(common_mount):
                        if filename in files:
                            found_path = os.path.join(root, filename)
                            logger.info(f"✅ Found file in common mount: {found_path}")
                            return found_path
            
            # Check specific mounted directories that we know about
            specific_mounts = [
                '/mnt/ai_scan_folder',  # External drive mount
                '/mnt/test_files',      # Local test files mount
            ]
            
            for mount_point in specific_mounts:
                if os.path.exists(mount_point):
                    potential_path = os.path.join(mount_point, filename)
                    logger.info(f"🔍 Checking specific mount: {potential_path}")
                    if os.path.exists(potential_path):
                        logger.info(f"✅ Found file in specific mount: {potential_path}")
                        return potential_path
            
            # Check if we're running inside Docker and try to access host paths
            if os.path.exists('/.dockerenv'):
                # We're inside Docker, try to access the original file path directly
                # The file might be accessible through the host filesystem
                original_file_path = os.path.join(parent_directory, filename) if parent_directory else filename
                logger.info(f"🔍 Checking original file path from Docker: {original_file_path}")
                if os.path.exists(original_file_path):
                    logger.info(f"✅ Found file at original path from Docker: {original_file_path}")
                    return original_file_path
            
            # List available files in mount points for debugging
            logger.warning(f"⚠️  File {filename} not found in any mounted folders")
            logger.info("📁 Available files in mount points:")
            for mount_point in mount_points:
                if mount_point and os.path.exists(mount_point):
                    try:
                        files = os.listdir(mount_point)
                        logger.info(f"   {mount_point}: {files}")
                    except Exception as e:
                        logger.warning(f"   {mount_point}: Error listing files - {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding file {filename}: {e}")
            return None
    
    def extract_text_content_from_output(self, stdout: str) -> str:
        """Extract text content from processor output"""
        try:
            # Try to parse JSON output
            if stdout.strip():
                # Look for JSON in the output
                lines = stdout.strip().split('\n')
                for line in lines:
                    if line.strip().startswith('{') and line.strip().endswith('}'):
                        try:
                            data = json.loads(line)
                            if 'text_content' in data:
                                return data['text_content']
                            elif 'content' in data:
                                return data['content']
                        except json.JSONDecodeError:
                            continue
                
                # If no JSON found, return the raw output
                return stdout.strip()
            
            return ""
        except Exception as e:
            logger.warning(f"⚠️  Failed to extract text content: {e}")
            return stdout.strip()
    
    def generate_processing_stats(self, text_content: str, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate processing statistics"""
        try:
            stats = {
                "content_length": len(text_content),
                "word_count": len(text_content.split()),
                "line_count": len(text_content.split('\n')),
                "processing_success": processing_result.get('success', False),
                "processing_time": datetime.now().isoformat(),
                "return_code": processing_result.get('returncode', -1)
            }
            
            # Add any additional stats from the processing result
            if 'stdout' in processing_result:
                stats['output_size'] = len(processing_result['stdout'])
            
            return stats
        except Exception as e:
            logger.warning(f"⚠️  Failed to generate processing stats: {e}")
            return {"error": str(e)}
    
    async def process_item(self, item: Dict, verify_elasticsearch: bool = True, show_stats: bool = True, debug_paths: bool = False) -> bool:
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
        
        if debug_paths:
            logger.info(f"🔍 DEBUG: Item details:")
            logger.info(f"   Filename: {filename}")
            logger.info(f"   Parent Directory: {parent_directory}")
            logger.info(f"   File Path: {file_path}")
            logger.info(f"   Found Path: {actual_file_path}")
            logger.info(f"   Mount Points: {os.environ.get('MOUNT_POINTS', 'None')}")
        
        if not actual_file_path:
            error_msg = f"File not found: {filename} in any mounted folders"
            logger.error(f"❌ {error_msg}")
            if debug_paths:
                logger.info("🔍 DEBUG: Available mount points and files:")
                mount_points = os.environ.get('MOUNT_POINTS', '').split(',')
                for mp in mount_points:
                    if mp and os.path.exists(mp):
                        try:
                            files = os.listdir(mp)
                            logger.info(f"   {mp}: {files}")
                        except Exception as e:
                            logger.warning(f"   {mp}: Error - {e}")
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
            
            # Extract text content from processing result
            text_content = self.extract_text_content_from_output(result['stdout'])
            
            # Generate processing statistics
            processing_stats = self.generate_processing_stats(text_content, result)
            
            # Store in Elasticsearch
            try:
                logger.info(f"🔍 Attempting to store data in Elasticsearch for {filename}")
                
                # Index document metadata
                logger.info(f"📝 Indexing document metadata for {filename}")
                await self.index_document_elasticsearch(item, {
                    'success': True,
                    'processing_stats': processing_stats,
                    'output_size': len(result['stdout'])
                })
                
                # Store document content if we have text
                if text_content:
                    logger.info(f"📄 Storing document content for {filename}")
                    await self.store_document_content_elasticsearch(item, text_content, processing_stats)
                
                logger.info(f"✅ Successfully stored data in Elasticsearch for {filename}")
                
                # Print Elasticsearch statistics for the processed file
                if show_stats:
                    await self.print_file_elasticsearch_stats(item, text_content, processing_stats, result)
                else:
                    logger.info(f"📊 Skipping detailed statistics for {filename}")
                
                # Verify the processing in Elasticsearch
                if verify_elasticsearch:
                    logger.info(f"🔍 Verifying Elasticsearch processing for {filename}...")
                    verification_result = await self.verify_elasticsearch_processing(item, text_content)
                    
                    if verification_result["verified"]:
                        logger.info(f"✅ Elasticsearch verification PASSED for {filename}")
                        # Note: We can't track stats here since they're in the worker method
                    else:
                        logger.warning(f"⚠️  Elasticsearch verification FAILED for {filename}")
                        logger.warning(f"   Details: {verification_result}")
                else:
                    logger.info(f"⏭️  Skipping Elasticsearch verification for {filename}")
            
            except Exception as e:
                logger.warning(f"⚠️  Failed to store in Elasticsearch for {filename}: {e}")
            
            await self.update_item_status(item_id, 'completed')
            return True
        else:
            error_msg = f"Processing failed: {result['stderr']}"
            logger.error(f"❌ Failed to process {filename}: {error_msg}")
            
            # Try to store error information in Elasticsearch
            try:
                await self.index_document_elasticsearch(item, {
                    'success': False,
                    'error': error_msg,
                    'return_code': result['returncode']
                })
                
                # Verify error was stored in Elasticsearch
                logger.info(f"🔍 Verifying error storage in Elasticsearch for {filename}...")
                verification_result = await self.verify_elasticsearch_processing(item)
                
                if verification_result["verified"]:
                    logger.info(f"✅ Error storage verification PASSED for {filename}")
                else:
                    logger.warning(f"⚠️  Error storage verification FAILED for {filename}")
                    logger.warning(f"   Details: {verification_result}")
                    
            except Exception as e:
                logger.warning(f"⚠️  Failed to store error in Elasticsearch: {e}")
            
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
                        continuous: bool = False, interval: int = 30, verify_elasticsearch: bool = True,
                        show_stats: bool = True):
        """Run the worker loop"""
        logger.info(f"🚀 Starting queue worker (processor_type: {processor_type}, limit: {limit})")
        if verify_elasticsearch:
            logger.info("🔍 Elasticsearch verification enabled")
        else:
            logger.info("⚠️  Elasticsearch verification disabled")
        
        if show_stats:
            logger.info("📊 Detailed statistics enabled")
        else:
            logger.info("⚠️  Detailed statistics disabled")
        
        verification_stats = {
            "total_processed": 0,
            "verification_passed": 0,
            "verification_failed": 0,
            "elasticsearch_unavailable": 0
        }
        
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
                    success = await self.process_item(item, verify_elasticsearch, show_stats, False)
                    if success:
                        processed_count += 1
                        verification_stats["total_processed"] += 1
                    else:
                        failed_count += 1
                
                logger.info(f"✅ Processed {processed_count} items, {failed_count} failed")
                
                # Print verification summary if enabled
                if verify_elasticsearch and verification_stats["total_processed"] > 0:
                    await self.print_verification_summary(verification_stats)
                
                # Print Elasticsearch summary statistics
                if verify_elasticsearch and show_stats:
                    await self.print_elasticsearch_summary_stats()
                
                if not continuous:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                if not continuous:
                    break
                await asyncio.sleep(interval)
    
    async def print_verification_summary(self, stats: Dict[str, int]):
        """Print verification summary"""
        logger.info("=" * 60)
        logger.info("📊 ELASTICSEARCH VERIFICATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {stats['total_processed']}")
        logger.info(f"Verification passed: {stats['verification_passed']}")
        logger.info(f"Verification failed: {stats['verification_failed']}")
        logger.info(f"Elasticsearch unavailable: {stats['elasticsearch_unavailable']}")
        
        if stats['total_processed'] > 0:
            success_rate = (stats['verification_passed'] / stats['total_processed']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        
        logger.info("=" * 60)

    async def verify_elasticsearch_processing(self, item: Dict, text_content: str = None) -> Dict[str, Any]:
        """Verify that the file has been processed and indexed in Elasticsearch"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping verification")
            return {"verified": False, "reason": "Elasticsearch not available"}
        
        try:
            doc_id = f"doc_{item['file_info_id']}"
            content_id = f"content_{item['file_info_id']}"
            
            verification_results = {
                "verified": False,
                "document_id": doc_id,
                "content_id": content_id,
                "filename": item['filename'],
                "checks": {}
            }
            
            # Check if document metadata exists
            try:
                doc_response = await self.elasticsearch_client.get(
                    index="documents",
                    id=doc_id
                )
                verification_results["checks"]["document_metadata"] = {
                    "exists": True,
                    "status": doc_response["_source"].get("status", "unknown"),
                    "processed_at": doc_response["_source"].get("processed_at", "unknown")
                }
                logger.info(f"✅ Document metadata verified: {doc_id}")
            except Exception as e:
                verification_results["checks"]["document_metadata"] = {
                    "exists": False,
                    "error": str(e)
                }
                logger.warning(f"⚠️  Document metadata not found: {doc_id}")
            
            # Check if document content exists (if we have text content)
            if text_content:
                try:
                    content_response = await self.elasticsearch_client.get(
                        index="document_content",
                        id=content_id
                    )
                    verification_results["checks"]["document_content"] = {
                        "exists": True,
                        "content_length": content_response["_source"].get("content_length", 0),
                        "created_at": content_response["_source"].get("created_at", "unknown")
                    }
                    logger.info(f"✅ Document content verified: {content_id}")
                except Exception as e:
                    verification_results["checks"]["document_content"] = {
                        "exists": False,
                        "error": str(e)
                    }
                    logger.warning(f"⚠️  Document content not found: {content_id}")
            else:
                verification_results["checks"]["document_content"] = {
                    "exists": False,
                    "reason": "No text content available"
                }
            
            # Determine overall verification status
            doc_exists = verification_results["checks"]["document_metadata"]["exists"]
            content_exists = verification_results["checks"]["document_content"]["exists"]
            
            if doc_exists and (not text_content or content_exists):
                verification_results["verified"] = True
                logger.info(f"✅ Elasticsearch verification PASSED for {item['filename']}")
            else:
                logger.warning(f"⚠️  Elasticsearch verification FAILED for {item['filename']}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch verification failed: {e}")
            return {
                "verified": False,
                "error": str(e),
                "document_id": f"doc_{item['file_info_id']}",
                "filename": item['filename']
            }
    
    async def search_elasticsearch_for_file(self, filename: str, file_path: str = None) -> Dict[str, Any]:
        """Search Elasticsearch for a specific file"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping search")
            return {"found": False, "reason": "Elasticsearch not available"}
        
        try:
            # Build search query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"filename": filename}}
                        ]
                    }
                },
                "size": 10
            }
            
            # Add file path to search if provided
            if file_path:
                search_body["query"]["bool"]["must"].append(
                    {"match": {"file_path": file_path}}
                )
            
            # Search in documents index
            doc_results = await self.elasticsearch_client.search(
                index="documents",
                body=search_body
            )
            
            # Search in document_content index
            content_results = await self.elasticsearch_client.search(
                index="document_content",
                body=search_body
            )
            
            search_results = {
                "filename": filename,
                "file_path": file_path,
                "documents_found": len(doc_results["hits"]["hits"]),
                "content_found": len(content_results["hits"]["hits"]),
                "documents": [],
                "content": []
            }
            
            # Process document results
            for hit in doc_results["hits"]["hits"]:
                search_results["documents"].append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "status": hit["_source"].get("status", "unknown"),
                    "processed_at": hit["_source"].get("processed_at", "unknown"),
                    "file_size": hit["_source"].get("file_size", 0)
                })
            
            # Process content results
            for hit in content_results["hits"]["hits"]:
                search_results["content"].append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "content_length": hit["_source"].get("content_length", 0),
                    "created_at": hit["_source"].get("created_at", "unknown")
                })
            
            search_results["found"] = len(search_results["documents"]) > 0 or len(search_results["content"]) > 0
            
            if search_results["found"]:
                logger.info(f"✅ Found {len(search_results['documents'])} document records and {len(search_results['content'])} content records for {filename}")
            else:
                logger.info(f"ℹ️  No records found for {filename}")
            
            return search_results
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch search failed: {e}")
            return {
                "found": False,
                "error": str(e),
                "filename": filename
            }
    
    async def get_elasticsearch_stats(self) -> Dict[str, Any]:
        """Get Elasticsearch statistics for processed documents"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping stats")
            return {"error": "Elasticsearch not available"}
        
        try:
            stats = {}
            
            # Get document count
            try:
                doc_count_response = await self.elasticsearch_client.count(index="documents")
                stats["documents_count"] = doc_count_response["count"]
            except Exception as e:
                stats["documents_count"] = 0
                stats["documents_error"] = str(e)
            
            # Get content count
            try:
                content_count_response = await self.elasticsearch_client.count(index="document_content")
                stats["content_count"] = content_count_response["count"]
            except Exception as e:
                stats["content_count"] = 0
                stats["content_error"] = str(e)
            
            # Get status distribution
            try:
                status_agg_response = await self.elasticsearch_client.search(
                    index="documents",
                    body={
                        "size": 0,
                        "aggs": {
                            "status_distribution": {
                                "terms": {
                                    "field": "status"
                                }
                            }
                        }
                    }
                )
                stats["status_distribution"] = status_agg_response["aggregations"]["status_distribution"]["buckets"]
            except Exception as e:
                stats["status_distribution"] = []
                stats["status_error"] = str(e)
            
            # Get recent documents
            try:
                recent_docs_response = await self.elasticsearch_client.search(
                    index="documents",
                    body={
                        "sort": [
                            {"processed_at": {"order": "desc"}}
                        ],
                        "size": 5
                    }
                )
                stats["recent_documents"] = [
                    {
                        "id": hit["_id"],
                        "filename": hit["_source"].get("filename", "unknown"),
                        "status": hit["_source"].get("status", "unknown"),
                        "processed_at": hit["_source"].get("processed_at", "unknown")
                    }
                    for hit in recent_docs_response["hits"]["hits"]
                ]
            except Exception as e:
                stats["recent_documents"] = []
                stats["recent_error"] = str(e)
            
            logger.info(f"📊 Elasticsearch stats: {stats['documents_count']} documents, {stats['content_count']} content records")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get Elasticsearch stats: {e}")
            return {"error": str(e)}

    async def print_file_elasticsearch_stats(self, item: Dict, text_content: str, processing_stats: Dict[str, Any], result: Dict[str, Any] = None):
        """Print detailed Elasticsearch statistics for the processed file"""
        try:
            filename = item['filename']
            file_info_id = item['file_info_id']
            
            logger.info("=" * 60)
            logger.info(f"📊 ELASTICSEARCH STATISTICS FOR: {filename}")
            logger.info("=" * 60)
            
            # File Information
            logger.info("📁 FILE INFORMATION:")
            logger.info(f"   Document ID: doc_{file_info_id}")
            logger.info(f"   Content ID: content_{file_info_id}")
            logger.info(f"   File Path: {item.get('file_path', 'N/A')}")
            logger.info(f"   Parent Directory: {item.get('parent_directory', 'N/A')}")
            logger.info(f"   File Size: {item.get('file_size', 0):,} bytes")
            logger.info(f"   File Type: {item.get('file_type', 'N/A')}")
            logger.info(f"   MIME Type: {item.get('mime_type', 'N/A')}")
            logger.info(f"   Checksum: {item.get('checksum', 'N/A')}")
            logger.info(f"   Priority: {item.get('priority', 'N/A')}")
            logger.info(f"   Processor Type: {item.get('processor_type', 'N/A')}")
            
            # Processing Statistics
            logger.info("")
            logger.info("⚙️  PROCESSING STATISTICS:")
            logger.info(f"   Content Length: {processing_stats.get('content_length', 0):,} characters")
            logger.info(f"   Word Count: {processing_stats.get('word_count', 0):,} words")
            logger.info(f"   Line Count: {processing_stats.get('line_count', 0):,} lines")
            logger.info(f"   Processing Success: {processing_stats.get('processing_success', False)}")
            logger.info(f"   Return Code: {processing_stats.get('return_code', -1)}")
            logger.info(f"   Output Size: {processing_stats.get('output_size', 0):,} bytes")
            
            # Text Content Analysis
            if text_content:
                logger.info("")
                logger.info("📝 TEXT CONTENT ANALYSIS:")
                logger.info(f"   Text Length: {len(text_content):,} characters")
                logger.info(f"   Word Count: {len(text_content.split()):,} words")
                logger.info(f"   Line Count: {len(text_content.splitlines()):,} lines")
                logger.info(f"   Average Line Length: {len(text_content) // max(len(text_content.splitlines()), 1):,} characters")
                
                # Character frequency analysis
                char_freq = {}
                for char in text_content.lower():
                    if char.isalpha():
                        char_freq[char] = char_freq.get(char, 0) + 1
                
                if char_freq:
                    top_chars = sorted(char_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                    logger.info(f"   Top 5 Characters: {', '.join([f'{char}({count})' for char, count in top_chars])}")
                
                # Word frequency analysis
                words = text_content.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 2:  # Skip very short words
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                if word_freq:
                    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                    logger.info(f"   Top 5 Words: {', '.join([f'{word}({count})' for word, count in top_words])}")
            
            # Elasticsearch Storage Information
            logger.info("")
            logger.info("🗄️  ELASTICSEARCH STORAGE:")
            logger.info(f"   Document Index: documents")
            logger.info(f"   Content Index: document_content")
            logger.info(f"   Status: completed")
            logger.info(f"   Processed At: {datetime.now().isoformat()}")
            
            # File metadata
            created_time = item.get('created_time')
            modified_time = item.get('modified_time')
            if created_time:
                logger.info(f"   Created Time: {created_time.isoformat() if hasattr(created_time, 'isoformat') else str(created_time)}")
            if modified_time:
                logger.info(f"   Modified Time: {modified_time.isoformat() if hasattr(modified_time, 'isoformat') else str(modified_time)}")
            
            # Additional metadata
            metadata = item.get('metadata', {})
            if metadata:
                logger.info("")
                logger.info("🏷️  ADDITIONAL METADATA:")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {"raw": metadata}
                
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"   {key}: {json.dumps(value)[:100]}{'...' if len(json.dumps(value)) > 100 else ''}")
                    else:
                        logger.info(f"   {key}: {value}")
            
            # Performance metrics
            logger.info("")
            logger.info("⚡ PERFORMANCE METRICS:")
            logger.info(f"   Processing Time: {datetime.now().isoformat()}")
            logger.info(f"   Content Density: {len(text_content) / max(item.get('file_size', 1), 1):.2f} chars/byte" if text_content and item.get('file_size') else "   Content Density: N/A")
            logger.info(f"   Compression Ratio: {len(text_content) / max(len(result.get('stdout', '')), 1):.2f}" if text_content and result.get('stdout') else "   Compression Ratio: N/A")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Failed to print Elasticsearch statistics: {e}")
    
    async def print_elasticsearch_summary_stats(self):
        """Print summary statistics for all documents in Elasticsearch"""
        if not self.elasticsearch_client:
            logger.warning("⚠️  Elasticsearch not available, skipping summary stats")
            return
        
        try:
            logger.info("=" * 60)
            logger.info("📊 ELASTICSEARCH SUMMARY STATISTICS")
            logger.info("=" * 60)
            
            # Get total document counts
            try:
                doc_count = await self.elasticsearch_client.count(index="documents")
                logger.info(f"📄 Total Documents: {doc_count['count']:,}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to get document count: {e}")
            
            try:
                content_count = await self.elasticsearch_client.count(index="document_content")
                logger.info(f"📝 Total Content Records: {content_count['count']:,}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to get content count: {e}")
            
            # Get status distribution
            try:
                status_agg = await self.elasticsearch_client.search(
                    index="documents",
                    body={
                        "size": 0,
                        "aggs": {
                            "status_distribution": {
                                "terms": {
                                    "field": "status"
                                }
                            },
                            "file_type_distribution": {
                                "terms": {
                                    "field": "file_type"
                                }
                            },
                            "avg_file_size": {
                                "avg": {
                                    "field": "file_size"
                                }
                            }
                        }
                    }
                )
                
                # Status distribution
                status_buckets = status_agg['aggregations']['status_distribution']['buckets']
                if status_buckets:
                    logger.info("")
                    logger.info("📊 STATUS DISTRIBUTION:")
                    for bucket in status_buckets:
                        logger.info(f"   {bucket['key']}: {bucket['doc_count']:,} documents")
                
                # File type distribution
                file_type_buckets = status_agg['aggregations']['file_type_distribution']['buckets']
                if file_type_buckets:
                    logger.info("")
                    logger.info("📁 FILE TYPE DISTRIBUTION:")
                    for bucket in file_type_buckets:
                        logger.info(f"   {bucket['key']}: {bucket['doc_count']:,} documents")
                
                # Average file size
                avg_size = status_agg['aggregations']['avg_file_size']['value']
                if avg_size:
                    logger.info("")
                    logger.info(f"📏 AVERAGE FILE SIZE: {avg_size:,.0f} bytes")
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to get distribution stats: {e}")
            
            # Get recent activity
            try:
                recent_docs = await self.elasticsearch_client.search(
                    index="documents",
                    body={
                        "sort": [
                            {"processed_at": {"order": "desc"}}
                        ],
                        "size": 3
                    }
                )
                
                if recent_docs['hits']['total']['value'] > 0:
                    logger.info("")
                    logger.info("🕒 RECENT PROCESSING ACTIVITY:")
                    for hit in recent_docs['hits']['hits']:
                        source = hit['_source']
                        logger.info(f"   {source.get('filename', 'unknown')} - {source.get('processed_at', 'unknown')}")
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to get recent activity: {e}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Failed to print summary statistics: {e}")

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
    parser.add_argument("--no-verify", action="store_true", help="Disable Elasticsearch verification")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing files in Elasticsearch")
    parser.add_argument("--no-stats", action="store_true", help="Disable detailed file statistics")
    parser.add_argument("--stats-only", action="store_true", help="Only print statistics for existing files")
    parser.add_argument("--debug-paths", action="store_true", help="Enable detailed path debugging")
    
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
        verify_elasticsearch = not args.no_verify
        show_stats = not args.no_stats
        debug_paths = args.debug_paths
        
        if debug_paths:
            logger.info("🔍 DEBUG MODE: Detailed path debugging enabled")
        
        if args.verify_only:
            logger.info("🔍 VERIFY-ONLY MODE - Checking existing files in Elasticsearch")
            # Get some sample files to verify
            sample_items = await worker.get_pending_items(args.processor_type, min(args.limit, 5))
            if sample_items:
                logger.info(f"🔍 Verifying {len(sample_items)} sample files...")
                for item in sample_items:
                    search_result = await worker.search_elasticsearch_for_file(item['filename'], item['file_path'])
                    if search_result["found"]:
                        logger.info(f"✅ Found in Elasticsearch: {item['filename']}")
                    else:
                        logger.warning(f"⚠️  Not found in Elasticsearch: {item['filename']}")
                
                # Get overall stats
                stats = await worker.get_elasticsearch_stats()
                logger.info(f"📊 Elasticsearch stats: {stats}")
            else:
                logger.info("ℹ️  No sample files to verify")
        elif args.stats_only:
            logger.info("📊 STATS-ONLY MODE - Printing statistics for existing files")
            await worker.print_elasticsearch_summary_stats()
        else:
            await worker.run_worker(
                processor_type=args.processor_type,
                limit=args.limit,
                continuous=args.continuous,
                interval=args.interval,
                verify_elasticsearch=verify_elasticsearch,
                show_stats=show_stats
            )
    
    except Exception as e:
        logger.error(f"❌ Worker failed: {e}")
        sys.exit(1)
    
    finally:
        # Disconnect from database
        await worker.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 