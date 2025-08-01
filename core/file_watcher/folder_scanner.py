#!/usr/bin/env python3
"""
Folder Scanner Utility for MDIS File Processing

This utility can scan any folder and process all files and subfolders within it,
using the same processing logic as the file watcher service.

Usage:
    python folder_scanner.py /path/to/folder
    python folder_scanner.py /path/to/folder --recursive
    python folder_scanner.py /path/to/folder --dry-run
    python folder_scanner.py /path/to/folder --max-depth 3
"""

import os
import sys
import argparse
import asyncio
import httpx
import mimetypes
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Write logs to stdout instead of stderr
)
logger = logging.getLogger(__name__)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://localhost:8001")
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.txt': 'text/plain',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.csv': 'text/csv',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel'
}

class FolderScanner:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.processed_files = []
        self.error_files = []
        self.skipped_files = []
        self.processing_files = set()
        
    def _convert_container_path_to_shared_volume_path(self, container_path: str) -> str:
        """Convert container path to shared volume path"""
        try:
            # If it's already a shared volume path, return as is
            if container_path.startswith('/app/scan_folders/'):
                return container_path
            
            # If it's a scan folder path, try to find it in shared volume
            if container_path.startswith('/app/scan_folder/'):
                filename = Path(container_path).name
                # Try to find the file in any mounted folder in shared volume
                for folder_name in self._get_mounted_folders():
                    shared_path = f"/app/scan_folders/{folder_name}/{filename}"
                    if Path(shared_path).exists():
                        logger.info(f"Found file in shared volume: {shared_path}")
                        return shared_path
                
                # If not found, try the default ai_scan_folder path
                shared_path = f"/app/scan_folders/ai_scan_folder/{filename}"
                logger.info(f"Converted container path {container_path} to shared volume path {shared_path}")
                return shared_path
            
            # For other paths, return as is
            return container_path
            
        except Exception as e:
            logger.error(f"Error converting container path {container_path} to shared volume path: {e}")
            return container_path
    
    def _get_mounted_folders(self) -> List[str]:
        """Get list of mounted folders in shared volume"""
        try:
            # Use a simple approach to list directories in the shared volume
            scan_folders_path = Path("/app/scan_folders")
            if scan_folders_path.exists():
                folders = [d.name for d in scan_folders_path.iterdir() if d.is_dir()]
                return folders
            return []
        except Exception as e:
            logger.warning(f"Error getting mounted folders: {e}")
            return []

    def _is_valid_file(self, file_path: str) -> bool:
        """Check if file is valid for processing"""
        try:
            # Check file extension
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                return False
            
            # Check file size (max 100MB)
            file_size = os.path.getsize(file_path)
            if file_size == 0 or file_size > 100 * 1024 * 1024:  # 100MB
                return False
            
            return True
        except Exception:
            return False
    
    async def _generate_file_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            return ""
    
    def _detect_document_type(self, filename: str) -> str:
        """Detect document type from filename"""
        ext = Path(filename).suffix.lower()
        
        if ext in ['.pdf']:
            return 'pdf'
        elif ext in ['.docx', '.doc']:
            return 'docx'
        elif ext in ['.txt', '.html', '.htm']:
            return 'txt'
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return 'image'
        elif ext in ['.csv', '.xlsx', '.xls']:
            return 'spreadsheet'
        else:
            return 'unknown'
    
    async def _create_document_metadata(self, file_path: str, source_folder: str) -> Dict:
        """Create document metadata for processing"""
        try:
            file_path_obj = Path(file_path)
            file_size = os.path.getsize(file_path)
            
            # Generate file hash
            file_hash = await self._generate_file_hash(file_path)
            
            # Detect MIME type
            mime_type = SUPPORTED_EXTENSIONS.get(file_path_obj.suffix.lower())
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path)
            
            # Store the original file path before any container path conversion
            original_file_path = file_path  # Keep the original host path
            
            # Always use container path format for external folders
            # This ensures the processing pipeline's dynamic mounting logic works correctly
            if '/media/lie/DATA2/ai_scan_folder' in file_path:
                container_file_path = file_path.replace('/media/lie/DATA2/ai_scan_folder', '/app/scan_folder')
                logger.info(f"Converting external path to container path: {file_path} -> {container_file_path}")
                file_path = container_file_path
            elif '/app/scan_folder' not in file_path and not file_path.startswith('/app/'):
                # For any other external path, convert to a container path
                # Extract the folder name and use it as the mount point
                folder_name = os.path.basename(os.path.dirname(file_path))
                container_file_path = f"/app/scan_folder/{os.path.basename(file_path)}"
                logger.info(f"Converting external path to container path: {file_path} -> {container_file_path}")
                file_path = container_file_path
            else:
                # If the path is already in container format, we need to reconstruct the original host path
                # This happens when the folder scanner is run from within a container
                if file_path.startswith('/app/scan_folder/'):
                    # We're in a container, so we need to convert the container path back to the host path
                    # For now, we'll use a simple approach: get the host path from environment variables
                    host_base_path = os.environ.get('HOST_SCAN_FOLDER_PATH')
                    if host_base_path:
                        # Convert container path to host path
                        filename = os.path.basename(file_path)
                        original_file_path = os.path.join(host_base_path, filename)
                        logger.info(f"Converting container path to host path: {file_path} -> {original_file_path}")
                    else:
                        # Fallback: use the container path as the original path
                        # The processing pipeline will handle the mounting
                        original_file_path = file_path
                        logger.warning(f"Could not determine host path for {file_path}, using container path as fallback")
            
            # Prepare metadata with original file path
            metadata = {
                "filename": file_path_obj.name,
                "file_path": file_path,  # Use container path for processing
                "file_size": file_size,
                "file_hash": file_hash,
                "mime_type": mime_type,
                "source": "folder_scanner",
                "source_folder": source_folder,
                "uploaded_at": datetime.utcnow().isoformat(),
                "processing_status": "pending",
                "original_file_path": original_file_path,  # Store original local path
                "data_source_type": "file_system",
                "data_source_uri": original_file_path,
                "metadata": {
                    "original_file_path": original_file_path,  # Also store in metadata for backward compatibility
                    "data_source_type": "file_system",
                    "data_source_uri": original_file_path
                }
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error creating document metadata for {file_path}: {e}")
            raise
    
    async def _send_to_processor(self, metadata: Dict) -> Optional[Dict]:
        """Send document to core processor"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send to processor: {metadata['filename']}")
            return {"document_id": "dry_run_document_id"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{CORE_PROCESSOR_URL}/documents/upload",
                    json=metadata,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Processor returned error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error sending to processor: {e}")
            return None
    
    async def _mark_as_processed(self, file_path: str):
        """Mark file as processed (no file movement)"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would mark as processed: {file_path}")
            return
            
        try:
            logger.info(f"File processed successfully: {file_path}")
        except Exception as e:
            logger.error(f"Error marking file as processed: {e}")
    
    async def _mark_as_error(self, file_path: str, error_message: str):
        """Mark file as error (no file movement)"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would mark as error: {file_path} (Error: {error_message})")
            return
            
        try:
            logger.error(f"File processing failed: {file_path} - {error_message}")
        except Exception as e:
            logger.error(f"Error marking file as error: {e}")
    
    async def process_document(self, file_path: str, source_folder: str):
        """Process a single document"""
        if file_path in self.processing_files:
            logger.info(f"File already being processed: {file_path}")
            return
        
        self.processing_files.add(file_path)
        
        try:
            # Validate file
            if not self._is_valid_file(file_path):
                logger.warning(f"Invalid file type or size: {file_path}")
                self.skipped_files.append({
                    "file_path": file_path,
                    "reason": "Invalid file type or size",
                    "skipped_at": datetime.utcnow().isoformat()
                })
                return
            
            # Create document metadata
            metadata = await self._create_document_metadata(file_path, source_folder)
            
            # Send to core processor
            result = await self._send_to_processor(metadata)
            
            if result:
                # Mark as processed (no file movement)
                await self._mark_as_processed(file_path)
                self.processed_files.append({
                    "file_path": file_path,
                    "processed_at": datetime.utcnow().isoformat(),
                    "document_id": result.get("document_id")
                })
                logger.info(f"Successfully processed: {file_path}")
            else:
                # Mark as error (no file movement)
                await self._mark_as_error(file_path, "Processing failed")
                self.error_files.append({
                    "file_path": file_path,
                    "error_at": datetime.utcnow().isoformat(),
                    "error": "Processing failed"
                })
                logger.error(f"Failed to process: {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            await self._mark_as_error(file_path, str(e))
            self.error_files.append({
                "file_path": file_path,
                "error_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
        finally:
            self.processing_files.discard(file_path)
    
    def scan_folder(self, folder_path: str, recursive: bool = True, max_depth: int = None) -> List[str]:
        """Scan folder and return list of files to process"""
        files_to_process = []
        folder_path = Path(folder_path).resolve()
        
        if not folder_path.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return files_to_process
        
        if not folder_path.is_dir():
            logger.error(f"Path is not a directory: {folder_path}")
            return files_to_process
        
        logger.info(f"Scanning folder: {folder_path}")
        
        if recursive:
            # Recursive scan
            for root, dirs, files in os.walk(folder_path):
                # Check max depth
                if max_depth is not None:
                    current_depth = len(Path(root).relative_to(folder_path).parts)
                    if current_depth > max_depth:
                        continue
                
                for file in files:
                    file_path = Path(root) / file
                    if self._is_valid_file(str(file_path)):
                        files_to_process.append(str(file_path))
        else:
            # Non-recursive scan
            for item in folder_path.iterdir():
                if item.is_file() and self._is_valid_file(str(item)):
                    files_to_process.append(str(item))
        
        logger.info(f"Found {len(files_to_process)} files to process")
        return files_to_process
    
    async def process_folder_queued(self, folder_path: str, recursive: bool = True, max_depth: int = None, 
                                   concurrent_limit: int = 5):
        """Process all files in a folder using queue-based approach to prevent race conditions"""
        files_to_process = self.scan_folder(folder_path, recursive, max_depth)
        
        if not files_to_process:
            logger.info("No files to process")
            return
        
        logger.info(f"Processing {len(files_to_process)} files using queue-based approach...")
        
        # Process files one at a time using a queue to prevent race conditions
        # This ensures only one document is being processed at any given time
        
        import asyncio
        from collections import deque
        
        # Create a queue of files to process
        file_queue = deque(files_to_process)
        processed_count = 0
        failed_count = 0
        
        while file_queue:
            file_path = file_queue.popleft()
            processed_count += 1
            
            logger.info(f"Processing file {processed_count}/{len(files_to_process)}: {os.path.basename(file_path)}")
            
            try:
                # Upload document first - the core processor will automatically trigger processing
                await self.process_document(file_path, folder_path)
                logger.info(f"✅ Uploaded file {processed_count}/{len(files_to_process)}: {os.path.basename(file_path)}")
                
                # Note: The core processor automatically triggers the processing pipeline
                # No need to manually trigger it here
                logger.info(f"✅ Processing automatically triggered by core processor for file {processed_count}/{len(files_to_process)}: {os.path.basename(file_path)}")
                
                # Small delay to ensure status updates are processed
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Failed to process file {processed_count}/{len(files_to_process)}: {os.path.basename(file_path)} - {e}")
                
                # Add file back to queue for retry (optional)
                # file_queue.append(file_path)
                
                # Continue with next file
                continue
        
        logger.info(f"Queue processing completed. Processed: {processed_count}, Failed: {failed_count}")
        
        # Print summary
        self.print_summary()

    async def process_folder_concurrent(self, folder_path: str, recursive: bool = True, max_depth: int = None, 
                                       concurrent_limit: int = 5):
        """Process all files in a folder concurrently with race condition prevention"""
        files_to_process = self.scan_folder(folder_path, recursive, max_depth)
        
        if not files_to_process:
            logger.info("No files to process")
            return
        
        logger.info(f"Processing {len(files_to_process)} files concurrently with race condition prevention...")
        
        # Process files with concurrency limit and race condition prevention
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def process_with_semaphore(file_path: str):
            async with semaphore:
                return await self.process_document_safe(file_path, folder_path)
        
        # Create tasks for all files
        tasks = [process_with_semaphore(file_path) for file_path in files_to_process]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"❌ Failed to process file {i+1}/{len(files_to_process)}: {result}")
            elif result:
                processed_count += 1
                logger.info(f"✅ Successfully processed file {i+1}/{len(files_to_process)}")
            else:
                failed_count += 1
                logger.error(f"❌ Failed to process file {i+1}/{len(files_to_process)}")
        
        logger.info(f"Concurrent processing completed. Processed: {processed_count}, Failed: {failed_count}")
        
        # Print summary
        self.print_summary()

    async def process_document_safe(self, file_path: str, source_folder: str):
        """Process a single document with race condition prevention"""
        if file_path in self.processing_files:
            logger.info(f"File already being processed: {file_path}")
            return False
        
        self.processing_files.add(file_path)
        
        try:
            # Validate file
            if not self._is_valid_file(file_path):
                logger.warning(f"Invalid file type or size: {file_path}")
                self.skipped_files.append({
                    "file_path": file_path,
                    "reason": "Invalid file type or size",
                    "skipped_at": datetime.utcnow().isoformat()
                })
                return False
            
            # Create document metadata
            metadata = await self._create_document_metadata(file_path, source_folder)
            
            # Send to core processor with retry logic
            result = await self._send_to_processor_with_retry(metadata)
            
            if result:
                # Mark as processed (no file movement)
                await self._mark_as_processed(file_path)
                self.processed_files.append({
                    "file_path": file_path,
                    "processed_at": datetime.utcnow().isoformat(),
                    "document_id": result.get("document_id")
                })
                logger.info(f"Successfully processed: {file_path}")
                
                # Trigger processing pipeline for concurrent mode
                # Note: The core processor automatically triggers the processing pipeline
                # No need to manually trigger it here
                logger.info(f"✅ Processing automatically triggered by core processor for {file_path}")
                
                return True
            else:
                # Mark as error (no file movement)
                await self._mark_as_error(file_path, "Processing failed")
                self.error_files.append({
                    "file_path": file_path,
                    "error_at": datetime.utcnow().isoformat(),
                    "error": "Processing failed"
                })
                logger.error(f"Failed to process: {file_path}")
                return False
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            await self._mark_as_error(file_path, str(e))
            self.error_files.append({
                "file_path": file_path,
                "error_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            return False
        finally:
            self.processing_files.discard(file_path)

    async def _send_to_processor_with_retry(self, metadata: Dict, max_retries: int = 3) -> Optional[Dict]:
        """Send document to core processor with retry logic and race condition prevention"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send to processor: {metadata['filename']}")
            return {"document_id": "dry_run_document_id"}
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{CORE_PROCESSOR_URL}/documents/upload",
                        json=metadata,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"Successfully uploaded document: {metadata['filename']}")
                        return result
                    else:
                        logger.error(f"Processor returned error: {response.status_code} - {response.text}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            return None
                            
            except Exception as e:
                logger.error(f"Error sending to processor (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                else:
                    return None
        
        return None

    async def process_folder(self, folder_path: str, recursive: bool = True, max_depth: int = None, 
                           concurrent_limit: int = 5):
        """Process all files in a folder"""
        files_to_process = self.scan_folder(folder_path, recursive, max_depth)
        
        if not files_to_process:
            logger.info("No files to process")
            return
        
        logger.info(f"Processing {len(files_to_process)} files...")
        
        # Process files sequentially to prevent race conditions in status updates
        # The processing pipeline is designed to handle one document at a time
        # Concurrent processing causes status updates to interfere with each other
        
        logger.info(f"Processing files sequentially to prevent status update race conditions")
        
        for i, file_path in enumerate(files_to_process, 1):
            logger.info(f"Processing file {i}/{len(files_to_process)}: {os.path.basename(file_path)}")
            try:
                await self.process_document(file_path, folder_path)
                logger.info(f"✅ Completed file {i}/{len(files_to_process)}: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"❌ Failed to process file {i}/{len(files_to_process)}: {os.path.basename(file_path)} - {e}")
                # Continue with next file instead of stopping
                continue
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Processed files: {len(self.processed_files)}")
        print(f"Error files: {len(self.error_files)}")
        print(f"Skipped files: {len(self.skipped_files)}")
        print(f"Total files: {len(self.processed_files) + len(self.error_files) + len(self.skipped_files)}")
        
        if self.error_files:
            print("\nError files:")
            for error_file in self.error_files:
                print(f"  - {error_file['file_path']}: {error_file['error']}")
        
        if self.skipped_files:
            print("\nSkipped files:")
            for skipped_file in self.skipped_files:
                print(f"  - {skipped_file['file_path']}: {skipped_file['reason']}")
        
        print("="*60)
    
    def save_report(self, report_path: str = None):
        """Save processing report to JSON file"""
        if report_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"folder_scan_report_{timestamp}.json"
        
        report = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "processed_files": self.processed_files,
            "error_files": self.error_files,
            "skipped_files": self.skipped_files,
            "summary": {
                "total_processed": len(self.processed_files),
                "total_errors": len(self.error_files),
                "total_skipped": len(self.skipped_files),
                "total_files": len(self.processed_files) + len(self.error_files) + len(self.skipped_files)
            }
        }
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")

def main():
    parser = argparse.ArgumentParser(description="Scan and process files in a folder")
    parser.add_argument("folder_path", help="Path to the folder to scan")
    parser.add_argument("--recursive", "-r", action="store_true", default=True,
                       help="Scan subdirectories recursively (default: True)")
    parser.add_argument("--max-depth", "-d", type=int, default=None,
                       help="Maximum depth for recursive scanning")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be processed without actually processing")
    parser.add_argument("--concurrent", "-c", type=int, default=5,
                       help="Number of concurrent processing tasks (default: 5)")
    parser.add_argument("--save-report", "-s", type=str, default=None,
                       help="Save processing report to JSON file")
    parser.add_argument("--no-recursive", action="store_true",
                       help="Disable recursive scanning")
    parser.add_argument("--sequential", action="store_true",
                       help="Use sequential processing instead of concurrent (slower but safer)")
    parser.add_argument("--queue", action="store_true",
                       help="Use queue-based processing (best for large batches)")
    
    args = parser.parse_args()
    
    # Handle recursive flag
    recursive = args.recursive and not args.no_recursive
    
    # Create scanner
    scanner = FolderScanner(dry_run=args.dry_run)
    
    # Process folder based on processing mode
    try:
        if args.sequential:
            logger.info("Using sequential processing mode")
            asyncio.run(scanner.process_folder(
                folder_path=args.folder_path,
                recursive=recursive,
                max_depth=args.max_depth,
                concurrent_limit=args.concurrent
            ))
        elif args.queue:
            logger.info("Using queue-based processing mode")
            asyncio.run(scanner.process_folder_queued(
                folder_path=args.folder_path,
                recursive=recursive,
                max_depth=args.max_depth,
                concurrent_limit=args.concurrent
            ))
        else:
            logger.info("Using concurrent processing mode (default)")
            asyncio.run(scanner.process_folder_concurrent(
                folder_path=args.folder_path,
                recursive=recursive,
                max_depth=args.max_depth,
                concurrent_limit=args.concurrent
            ))
        
        # Save report if requested
        if args.save_report:
            scanner.save_report(args.save_report)
        elif not args.dry_run:
            # Auto-save report for non-dry-run operations
            scanner.save_report()
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 