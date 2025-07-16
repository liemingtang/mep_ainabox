from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

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
DOCUMENT_ROUTER_URL = os.getenv("DOCUMENT_ROUTER_URL", "http://document-router:8002")
WATCH_PATHS = os.getenv("WATCH_PATHS", "./watch_folder")

# File watcher setup
class DocumentHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print(f"New document detected: {event.src_path}")
            # In a real implementation, this would send the file to the document router
            self.process_document(event.src_path)
    
    def process_document(self, file_path):
        try:
            # Basic processing - in a real implementation, this would send the file
            # to the document router for processing
            print(f"Processing document: {file_path}")
        except Exception as e:
            print(f"Error processing document {file_path}: {str(e)}")

# Initialize file watcher
observer = Observer()
event_handler = DocumentHandler()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "file-watcher"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MDIS File Watcher",
        "version": "1.0.0",
        "watch_paths": WATCH_PATHS,
        "document_router": DOCUMENT_ROUTER_URL
    }

@app.post("/api/v1/watch/start")
async def start_watching():
    """Start watching for new documents"""
    try:
        # Start the file watcher
        observer.schedule(event_handler, WATCH_PATHS, recursive=False)
        observer.start()
        return {"status": "started", "message": "File watcher started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting file watcher: {str(e)}")

@app.post("/api/v1/watch/stop")
async def stop_watching():
    """Stop watching for new documents"""
    try:
        observer.stop()
        observer.join()
        return {"status": "stopped", "message": "File watcher stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping file watcher: {str(e)}")

@app.get("/api/v1/watch/status")
async def get_watch_status():
    """Get the status of the file watcher"""
    try:
        return {
            "status": "running" if observer.is_alive() else "stopped",
            "watch_paths": WATCH_PATHS,
            "is_alive": observer.is_alive()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting watch status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Start the file watcher in a separate thread
    def start_watcher():
        observer.schedule(event_handler, WATCH_PATHS, recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    
    watcher_thread = threading.Thread(target=start_watcher, daemon=True)
    watcher_thread.start()
    
    uvicorn.run(app, host="0.0.0.0", port=8009) 