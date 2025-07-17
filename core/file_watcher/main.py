from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import mimetypes
import hashlib
import shutil
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
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "./processed")
ERROR_FOLDER = os.getenv("ERROR_FOLDER", "./error")

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
        """Process a detected document"""
        if file_path in self.processing_files:
            logger.info(f"File already being processed: {file_path}")
            return
        
        self.processing_files.add(file_path)
        
        try:
            # Wait a moment to ensure file is fully written
            await asyncio.sleep(1)
            
            # Check if file still exists and is accessible
            if not os.path.exists(file_path):
                logger.warning(f"File no longer exists: {file_path}")
                return
            
            # Validate file
            if not self._is_valid_file(file_path):
                logger.warning(f"Invalid file type or size: {file_path}")
                await self._move_to_error_folder(file_path, "Invalid file type or size")
                return
            
            # Create document metadata
            metadata = await self._create_document_metadata(file_path)
            
            # Send to core processor
            result = await self._send_to_processor(metadata)
            
            if result:
                # Move to processed folder
                await self._move_to_processed_folder(file_path)
                watcher_state["processed_files"].append({
                    "file_path": file_path,
                    "processed_at": datetime.utcnow().isoformat(),
                    "document_id": result.get("document_id")
                })
                logger.info(f"Successfully processed: {file_path}")
            else:
                # Move to error folder
                await self._move_to_error_folder(file_path, "Processing failed")
                watcher_state["error_files"].append({
                    "file_path": file_path,
                    "error_at": datetime.utcnow().isoformat(),
                    "error": "Processing failed"
                })
                logger.error(f"Failed to process: {file_path}")
            
            watcher_state["last_activity"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            await self._move_to_error_folder(file_path, str(e))
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
    
    async def _move_to_processed_folder(self, file_path: str):
        """Move file to processed folder"""
        try:
            if not os.path.exists(PROCESSED_FOLDER):
                os.makedirs(PROCESSED_FOLDER, exist_ok=True)
            
            filename = Path(file_path).name
            dest_path = os.path.join(PROCESSED_FOLDER, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(PROCESSED_FOLDER, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, dest_path)
            logger.info(f"Moved to processed: {dest_path}")
            
        except Exception as e:
            logger.error(f"Error moving to processed folder: {e}")
    
    async def _move_to_error_folder(self, file_path: str, error_message: str):
        """Move file to error folder"""
        try:
            if not os.path.exists(ERROR_FOLDER):
                os.makedirs(ERROR_FOLDER, exist_ok=True)
            
            filename = Path(file_path).name
            dest_path = os.path.join(ERROR_FOLDER, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(ERROR_FOLDER, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.move(file_path, dest_path)
            logger.info(f"Moved to error folder: {dest_path}")
            
        except Exception as e:
            logger.error(f"Error moving to error folder: {e}")

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
        observer.schedule(event_handler, WATCH_PATHS, recursive=False)
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

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Start the file watcher in a separate thread
    def start_watcher():
        try:
            # Ensure watch folder exists
            os.makedirs(WATCH_PATHS, exist_ok=True)
            os.makedirs(PROCESSED_FOLDER, exist_ok=True)
            os.makedirs(ERROR_FOLDER, exist_ok=True)
            
            observer.schedule(event_handler, WATCH_PATHS, recursive=False)
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