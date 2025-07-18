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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://localhost:8001")

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
            
            # Create metadata
            metadata = {
                "filename": file_path_obj.name,
                "file_path": str(file_path),
                "file_size": file_size,
                "mime_type": mime_type,
                "file_hash": file_hash,
                "source": "folder_scanner",
                "processing_status": "pending",
                "document_type": self._detect_document_type(file_path_obj.name),
                "metadata": {
                    "scanned_folder": source_folder,
                    "scanned_at": datetime.utcnow().isoformat()
                }
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating metadata: {e}")
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
    
    async def process_folder(self, folder_path: str, recursive: bool = True, max_depth: int = None, 
                           concurrent_limit: int = 5):
        """Process all files in a folder"""
        files_to_process = self.scan_folder(folder_path, recursive, max_depth)
        
        if not files_to_process:
            logger.info("No files to process")
            return
        
        logger.info(f"Processing {len(files_to_process)} files...")
        
        # Process files with concurrency limit
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def process_with_semaphore(file_path: str):
            async with semaphore:
                await self.process_document(file_path, folder_path)
        
        # Create tasks for all files
        tasks = [process_with_semaphore(file_path) for file_path in files_to_process]
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
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
    
    args = parser.parse_args()
    
    # Handle recursive flag
    recursive = args.recursive and not args.no_recursive
    
    # Create scanner
    scanner = FolderScanner(dry_run=args.dry_run)
    
    # Process folder
    try:
        asyncio.run(scanner.process_folder(
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