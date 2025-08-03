#!/usr/bin/env python3
"""
Host-Side Volume Manager for Dynamic Folder Mounting

This service runs on the host system and can dynamically mount any local folder
to the shared Docker volume so processing containers can access it.
"""

import os
import sys
import subprocess
import json
import logging
import hashlib
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolumeManager:
    def __init__(self, volume_name: str = "shared_scan_folders"):
        self.volume_name = volume_name
        self.mount_point = "/app/scan_folders"  # This is the mount point inside containers
        
    def _generate_unique_folder_name(self, host_path: str, folder_name: str = None) -> str:
        """Generate a unique folder name for the shared volume"""
        host_path = Path(host_path).resolve()
        
        # Use provided folder name or basename
        if folder_name is None:
            folder_name = host_path.name
        
        # Create a unique identifier based on the full path
        path_hash = hashlib.md5(str(host_path).encode()).hexdigest()[:8]
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        
        # Combine folder name, hash, and timestamp for uniqueness
        unique_name = f"{folder_name}_{path_hash}_{timestamp}"
        
        logger.info(f"Generated unique folder name: {unique_name} for {host_path}")
        return unique_name
    
    def mount_folder(self, host_path: str, folder_name: str = None) -> str:
        """Mount a local folder to the shared volume and return the unique folder name"""
        try:
            logger.info(f"Original host path: {host_path}")
            
            # Store the original host path for Docker mounting
            original_host_path = host_path
            
            # Check if we're running inside a Docker container
            # If so, the host filesystem is mounted at /host
            if os.path.exists('/host'):
                logger.info(f"Running inside Docker container, host filesystem mounted at /host")
                # Convert host path to container path for existence check
                if not host_path.startswith('/host/'):
                    # If it's an absolute path, prepend /host
                    if host_path.startswith('/'):
                        host_path = f"/host{host_path}"
                        logger.info(f"Converted absolute path to: {host_path}")
                    else:
                        # If it's a relative path, make it absolute first
                        host_path = f"/host/{host_path}"
                        logger.info(f"Converted relative path to: {host_path}")
                else:
                    logger.info(f"Path already has /host prefix: {host_path}")
            else:
                logger.info(f"Running on host system, no path conversion needed")
            
            host_path = Path(host_path).resolve()
            logger.info(f"Resolved path: {host_path}")
            
            if not host_path.exists():
                logger.error(f"Host path does not exist: {host_path}")
                return None
                
            if not host_path.is_dir():
                logger.error(f"Host path is not a directory: {host_path}")
                return None
            
            # Generate unique folder name
            unique_folder_name = self._generate_unique_folder_name(host_path, folder_name)
            
            # Create a temporary container to copy files to the volume
            container_name = f"volume-mount-{unique_folder_name}-{os.getpid()}"
            
            logger.info(f"Mounting {original_host_path} to shared volume as {unique_folder_name}")
            
            # First, create the volume if it doesn't exist
            self._ensure_volume_exists()
            
            # Create a temporary container that mounts both the host path and the volume
            # Use the original host path for Docker mounting
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{original_host_path}:/source:ro",
                "-v", f"{self.volume_name}:/dest",
                "alpine:latest",
                "sh", "-c", f"mkdir -p /dest/{unique_folder_name} && cp -r /source/* /dest/{unique_folder_name}/"
            ]
            
            logger.info(f"Running: {' '.join(docker_cmd)}")
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully mounted {original_host_path} to shared volume as {unique_folder_name}")
                return unique_folder_name
            else:
                logger.error(f"Failed to mount folder: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error mounting folder: {e}")
            return None
    
    def mount_folder_concurrent(self, host_path: str, folder_name: str = None, max_retries: int = 3) -> str:
        """Mount a folder with retry logic for concurrent processing"""
        for attempt in range(max_retries):
            try:
                unique_name = self.mount_folder(host_path, folder_name)
                if unique_name:
                    return unique_name
                
                # If failed, wait a bit before retry
                if attempt < max_retries - 1:
                    time.sleep(1 + attempt * 0.5)  # Exponential backoff
                    
            except Exception as e:
                logger.warning(f"Mount attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 + attempt * 0.5)
        
        logger.error(f"Failed to mount folder after {max_retries} attempts")
        return None
    
    def unmount_folder(self, folder_name: str) -> bool:
        """Unmount a folder from the shared volume"""
        try:
            container_name = f"volume-unmount-{folder_name}-{os.getpid()}"
            
            logger.info(f"Unmounting {folder_name} from shared volume")
            
            # Create a temporary container to remove the folder from the volume
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{self.volume_name}:/dest",
                "alpine:latest",
                "sh", "-c", f"rm -rf /dest/{folder_name}"
            ]
            
            logger.info(f"Running: {' '.join(docker_cmd)}")
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully unmounted {folder_name} from shared volume")
                return True
            else:
                logger.error(f"Failed to unmount folder: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error unmounting folder: {e}")
            return False
    
    def list_mounted_folders(self) -> List[str]:
        """List all folders currently mounted in the shared volume"""
        try:
            container_name = f"volume-list-{os.getpid()}"
            
            # Create a temporary container to list the contents of the volume
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{self.volume_name}:/dest",
                "alpine:latest",
                "sh", "-c", "ls -la /dest"
            ]
            
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to get folder names
                lines = result.stdout.strip().split('\n')
                folders = []
                for line in lines:
                    if line.startswith('d'):  # Directory
                        parts = line.split()
                        if len(parts) >= 9:
                            folder_name = parts[-1]
                            if folder_name not in ['.', '..']:
                                folders.append(folder_name)
                return folders
            else:
                logger.error(f"Failed to list folders: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing folders: {e}")
            return []
    
    def _ensure_volume_exists(self):
        """Ensure the shared volume exists"""
        try:
            # Check if volume exists
            result = subprocess.run(
                ["docker", "volume", "ls", "-q", "-f", f"name={self.volume_name}"],
                capture_output=True, text=True
            )
            
            if not result.stdout.strip():
                # Create the volume
                logger.info(f"Creating volume {self.volume_name}")
                subprocess.run(["docker", "volume", "create", self.volume_name], check=True)
                
        except Exception as e:
            logger.error(f"Error ensuring volume exists: {e}")
            raise
    
    def cleanup_old_folders(self, max_age_hours: int = 24) -> int:
        """Clean up old mounted folders to prevent volume bloat"""
        try:
            folders = self.list_mounted_folders()
            cleaned_count = 0
            current_time = time.time()
            
            for folder in folders:
                # Extract timestamp from folder name (last 6 digits)
                try:
                    timestamp_str = folder.split('_')[-1]
                    if len(timestamp_str) == 6 and timestamp_str.isdigit():
                        folder_time = int(timestamp_str)
                        age_hours = (current_time - folder_time) / 3600
                        
                        if age_hours > max_age_hours:
                            logger.info(f"Cleaning up old folder: {folder} (age: {age_hours:.1f} hours)")
                            if self.unmount_folder(folder):
                                cleaned_count += 1
                except (ValueError, IndexError):
                    # Skip folders that don't follow the naming pattern
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} old folders")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old folders: {e}")
            return 0

# FastAPI app for the host volume manager service
app = FastAPI(title="Host Volume Manager", version="1.0.0")

# Pydantic models
class MountRequest(BaseModel):
    host_path: str
    folder_name: Optional[str] = None

class MountResponse(BaseModel):
    success: bool
    unique_folder_name: Optional[str] = None
    error_message: Optional[str] = None

class UnmountRequest(BaseModel):
    folder_name: str

class UnmountResponse(BaseModel):
    success: bool
    error_message: Optional[str] = None

class ListResponse(BaseModel):
    folders: List[str]

class CleanupResponse(BaseModel):
    cleaned_count: int

# Global volume manager instance
volume_manager = VolumeManager()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "host-volume-manager"}

@app.post("/mount", response_model=MountResponse)
async def mount_folder(request: MountRequest):
    """Mount a folder to the shared volume"""
    try:
        unique_folder_name = volume_manager.mount_folder_concurrent(
            request.host_path, 
            request.folder_name
        )
        
        if unique_folder_name:
            return MountResponse(
                success=True,
                unique_folder_name=unique_folder_name
            )
        else:
            return MountResponse(
                success=False,
                error_message="Failed to mount folder"
            )
            
    except Exception as e:
        logger.error(f"Error in mount endpoint: {e}")
        return MountResponse(
            success=False,
            error_message=str(e)
        )

@app.post("/unmount", response_model=UnmountResponse)
async def unmount_folder(request: UnmountRequest):
    """Unmount a folder from the shared volume"""
    try:
        success = volume_manager.unmount_folder(request.folder_name)
        
        if success:
            return UnmountResponse(success=True)
        else:
            return UnmountResponse(
                success=False,
                error_message="Failed to unmount folder"
            )
            
    except Exception as e:
        logger.error(f"Error in unmount endpoint: {e}")
        return UnmountResponse(
            success=False,
            error_message=str(e)
        )

@app.get("/list", response_model=ListResponse)
async def list_folders():
    """List all mounted folders"""
    try:
        folders = volume_manager.list_mounted_folders()
        return ListResponse(folders=folders)
        
    except Exception as e:
        logger.error(f"Error in list endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup", response_model=CleanupResponse)
async def cleanup_folders(max_age_hours: int = 24):
    """Clean up old folders"""
    try:
        cleaned_count = volume_manager.cleanup_old_folders(max_age_hours)
        return CleanupResponse(cleaned_count=cleaned_count)
        
    except Exception as e:
        logger.error(f"Error in cleanup endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """CLI interface for the volume manager"""
    parser = argparse.ArgumentParser(description="Host Volume Manager for Dynamic Folder Mounting")
    parser.add_argument("command", choices=["mount", "unmount", "list", "cleanup", "serve"], help="Command to execute")
    parser.add_argument("--path", help="Host path to mount (for mount command)")
    parser.add_argument("--name", help="Folder name in shared volume (for mount/unmount commands)")
    parser.add_argument("--volume", default="shared_scan_folders", help="Docker volume name")
    parser.add_argument("--max-age", type=int, default=24, help="Maximum age in hours for cleanup")
    parser.add_argument("--port", type=int, default=8011, help="Port for the service (for serve command)")
    
    args = parser.parse_args()
    
    if args.command == "serve":
        # Start the FastAPI service
        logger.info(f"Starting host volume manager service on port {args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # CLI mode
        volume_manager = VolumeManager(args.volume)
        
        if args.command == "mount":
            if not args.path:
                logger.error("--path is required for mount command")
                sys.exit(1)
            
            unique_name = volume_manager.mount_folder_concurrent(args.path, args.name)
            if unique_name:
                print(f"Successfully mounted as: {unique_name}")
                sys.exit(0)
            else:
                sys.exit(1)
            
        elif args.command == "unmount":
            if not args.name:
                logger.error("--name is required for unmount command")
                sys.exit(1)
            
            success = volume_manager.unmount_folder(args.name)
            sys.exit(0 if success else 1)
            
        elif args.command == "list":
            folders = volume_manager.list_mounted_folders()
            if folders:
                print("Mounted folders:")
                for folder in folders:
                    print(f"  - {folder}")
            else:
                print("No folders currently mounted")
            sys.exit(0)
            
        elif args.command == "cleanup":
            cleaned = volume_manager.cleanup_old_folders(args.max_age)
            print(f"Cleaned up {cleaned} old folders")
            sys.exit(0)

if __name__ == "__main__":
    main() 