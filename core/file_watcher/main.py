from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import mimetypes
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MDIS File Watcher", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
CORE_PROCESSOR_URL = os.getenv("CORE_PROCESSOR_URL", "http://core-processor:8001")
WATCH_PATHS = os.getenv("WATCH_PATHS", "./watch_folder")

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

# Pydantic models
class ScanFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    max_depth: Optional[int] = None
    concurrent_limit: int = 5
    dry_run: bool = False

# File watcher state
watcher_state = {
    "is_running": False,
    "processed_files": [],
    "error_files": [],
    "last_activity": None
}

class DocumentHandler(FileSystemEventHandler):
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.processing_files = set()
    
    def _get_shared_volume_path(self, file_path: str) -> str:
        """Convert file path to shared volume path if needed"""
        try:
            # If it's already a shared volume path, return as is
            if file_path.startswith('/app/scan_folders/'):
                return file_path
            
            # If it's a scan folder path, try to find it in shared volume
            if file_path.startswith('/app/scan_folder/'):
                filename = Path(file_path).name
                # Try to find the file in any mounted folder in shared volume
                for folder_name in self._get_mounted_folders():
                    shared_path = f"/app/scan_folders/{folder_name}/{filename}"
                    if Path(shared_path).exists():
                        logger.info(f"Found file in shared volume: {shared_path}")
                        return shared_path
                
                # If not found, try the default ai_scan_folder path
                shared_path = f"/app/scan_folders/ai_scan_folder/{filename}"
                logger.info(f"Converted container path {file_path} to shared volume path {shared_path}")
                return shared_path
            
            # For other paths, return as is
            return file_path
            
        except Exception as e:
            logger.warning(f"Error converting to shared volume path {file_path}: {e}")
            return file_path
    
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
    
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            logger.info(f"New document detected: {file_path}")
            
            # Process file asynchronously
            threading.Thread(target=self._process_file_async, args=(file_path,), daemon=True).start()
    
    def on_moved(self, event):
        if not event.is_directory:
            file_path = event.dest_path
            logger.info(f"Document moved to: {file_path}")
            
            # Process file asynchronously
            threading.Thread(target=self._process_file_async, args=(file_path,), daemon=True).start()
    
    def _process_file_async(self, file_path: str):
        """Process file asynchronously to avoid blocking the watcher"""
        try:
            # Use asyncio.run to run async function in thread
            import asyncio
            asyncio.run(self.process_document(file_path))
        except Exception as e:
            logger.error(f"Error in async processing: {e}")
    
    async def process_document(self, file_path: str):
        """Process a detected document with shared volume support"""
        if file_path in self.processing_files:
            logger.info(f"File already being processed: {file_path}")
            return
        
        self.processing_files.add(file_path)
        
        try:
            # Wait a moment to ensure file is fully written
            await asyncio.sleep(1)
            
            # Convert file path to shared volume path if needed
            file_path = self._get_shared_volume_path(file_path)
            
            # Check if file still exists and is accessible
            if not os.path.exists(file_path):
                logger.warning(f"File no longer exists: {file_path}")
                return
            
            # Validate file
            if not self._is_valid_file(file_path):
                logger.warning(f"Invalid file type or size: {file_path}")
                await self._mark_as_error(file_path, "Invalid file type or size")
                watcher_state["error_files"].append({
                    "file_path": file_path,
                    "error_at": datetime.utcnow().isoformat(),
                    "error": "Invalid file type or size"
                })
                return
            
            # Create document metadata
            metadata = await self._create_document_metadata(file_path)
            
            # Send to core processor
            result = await self._send_to_processor(metadata)
            
            if result:
                # Mark as processed (no file movement)
                await self._mark_as_processed(file_path)
                watcher_state["processed_files"].append({
                    "file_path": file_path,
                    "processed_at": datetime.utcnow().isoformat(),
                    "document_id": result.get("document_id")
                })
                logger.info(f"Successfully processed: {file_path}")
            else:
                # Mark as error (no file movement)
                await self._mark_as_error(file_path, "Processing failed")
                watcher_state["error_files"].append({
                    "file_path": file_path,
                    "error_at": datetime.utcnow().isoformat(),
                    "error": "Processing failed"
                })
                logger.error(f"Failed to process: {file_path}")
            
            watcher_state["last_activity"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            await self._mark_as_error(file_path, str(e))
            watcher_state["error_files"].append({
                "file_path": file_path,
                "error_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
        finally:
            self.processing_files.discard(file_path)
    
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
    
    async def _create_document_metadata(self, file_path: str) -> Dict:
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
                "source": "file_watcher",
                "processing_status": "pending",
                "document_type": self._detect_document_type(file_path_obj.name),
                "metadata": {
                    "watched_folder": WATCH_PATHS,
                    "detected_at": datetime.utcnow().isoformat()
                }
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating metadata: {e}")
            raise
    
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
    
    async def _send_to_processor(self, metadata: Dict) -> Optional[Dict]:
        """Send document to core processor"""
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
        try:
            logger.info(f"File processed successfully: {file_path}")
        except Exception as e:
            logger.error(f"Error marking file as processed: {e}")
    
    async def _mark_as_error(self, file_path: str, error_message: str):
        """Mark file as error (no file movement)"""
        try:
            logger.error(f"File processing failed: {file_path} - {error_message}")
        except Exception as e:
            logger.error(f"Error marking file as error: {e}")

# Initialize file watcher
observer = Observer()
event_handler = DocumentHandler()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "file-watcher",
        "watcher_running": watcher_state["is_running"]
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS File Watcher",
        "version": "1.0.0",
        "watch_paths": WATCH_PATHS,
        "core_processor": CORE_PROCESSOR_URL,
        "supported_extensions": list(SUPPORTED_EXTENSIONS.keys()),
        "status": watcher_state
    }

@app.post("/api/v1/watch/start")
async def start_watching():
    """Start watching for new documents"""
    try:
        if watcher_state["is_running"]:
            return {"status": "already_running", "message": "File watcher is already running"}
        
        # Ensure watch folder exists
        os.makedirs(WATCH_PATHS, exist_ok=True)
        
        # Start the file watcher
        observer.schedule(event_handler, WATCH_PATHS, recursive=True)
        observer.start()
        
        watcher_state["is_running"] = True
        watcher_state["last_activity"] = datetime.utcnow().isoformat()
        
        logger.info(f"File watcher started watching: {WATCH_PATHS}")
        return {"status": "started", "message": "File watcher started"}
        
    except Exception as e:
        logger.error(f"Error starting file watcher: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting file watcher: {str(e)}")

@app.post("/api/v1/watch/stop")
async def stop_watching():
    """Stop watching for new documents"""
    try:
        if not watcher_state["is_running"]:
            return {"status": "already_stopped", "message": "File watcher is already stopped"}
        
        observer.stop()
        observer.join()
        
        watcher_state["is_running"] = False
        watcher_state["last_activity"] = datetime.utcnow().isoformat()
        
        logger.info("File watcher stopped")
        return {"status": "stopped", "message": "File watcher stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping file watcher: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping file watcher: {str(e)}")

@app.get("/api/v1/watch/status")
async def get_watch_status():
    """Get the status of the file watcher"""
    try:
        return {
            "status": "running" if watcher_state["is_running"] else "stopped",
            "watch_paths": WATCH_PATHS,
            "is_alive": observer.is_alive(),
            "processed_files_count": len(watcher_state["processed_files"]),
            "error_files_count": len(watcher_state["error_files"]),
            "last_activity": watcher_state["last_activity"],
            "currently_processing": len(event_handler.processing_files)
        }
    except Exception as e:
        logger.error(f"Error getting watch status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting watch status: {str(e)}")

@app.get("/api/v1/watch/processed")
async def get_processed_files():
    """Get list of processed files"""
    return {
        "processed_files": watcher_state["processed_files"],
        "count": len(watcher_state["processed_files"])
    }

@app.get("/api/v1/watch/errors")
async def get_error_files():
    """Get list of error files"""
    return {
        "error_files": watcher_state["error_files"],
        "count": len(watcher_state["error_files"])
    }

@app.post("/api/v1/watch/clear-history")
async def clear_history():
    """Clear processing history"""
    watcher_state["processed_files"] = []
    watcher_state["error_files"] = []
    return {"status": "cleared", "message": "Processing history cleared"}

@app.post("/api/v1/watch/process-file")
async def process_specific_file(file_path: str):
    """Manually process a specific file"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Process the file
        await event_handler.process_document(file_path)
        
        return {"status": "processing", "message": f"File {file_path} sent for processing"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing specific file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/api/v1/watch/scan-folder")
async def scan_and_process_folder(request: ScanFolderRequest):
    """Scan and process all files in a folder"""
    try:
        if not os.path.exists(request.folder_path):
            raise HTTPException(status_code=404, detail="Folder not found")
        
        if not os.path.isdir(request.folder_path):
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        # Import the folder scanner
        from folder_scanner import FolderScanner
        
        # Create scanner instance
        scanner = FolderScanner(dry_run=request.dry_run)
        
        # Process the folder
        await scanner.process_folder(
            folder_path=request.folder_path,
            recursive=request.recursive,
            max_depth=request.max_depth,
            concurrent_limit=request.concurrent_limit
        )
        
        # Prepare response
        response = {
            "status": "completed",
            "folder_path": request.folder_path,
            "dry_run": request.dry_run,
            "summary": {
                "processed_files": len(scanner.processed_files),
                "error_files": len(scanner.error_files),
                "skipped_files": len(scanner.skipped_files),
                "total_files": len(scanner.processed_files) + len(scanner.error_files) + len(scanner.skipped_files)
            },
            "processed_files": scanner.processed_files,
            "error_files": scanner.error_files,
            "skipped_files": scanner.skipped_files
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error scanning folder: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Start the file watcher in a separate thread
    def start_watcher():
        try:
            # Ensure watch folder exists
            os.makedirs(WATCH_PATHS, exist_ok=True)
            
            observer.schedule(event_handler, WATCH_PATHS, recursive=True)
            observer.start()
            watcher_state["is_running"] = True
            watcher_state["last_activity"] = datetime.utcnow().isoformat()
            
            logger.info(f"File watcher started watching: {WATCH_PATHS}")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
        except Exception as e:
            logger.error(f"Error in watcher thread: {e}")
        finally:
            observer.join()
    
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    
    uvicorn.run(app, host="0.0.0.0", port=8009) 