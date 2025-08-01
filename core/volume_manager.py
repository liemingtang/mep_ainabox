#!/usr/bin/env python3
"""
Volume Manager for Dynamic Folder Mounting

This script manages the shared Docker volume for scan folders.
It can mount/unmount local folders to the shared volume so all processing services
can access any local folder without individual configuration.
Supports concurrent processing of multiple local folders.
"""

import os
import sys
import subprocess
import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolumeManager:
    def __init__(self, volume_name: str = "shared_scan_folders"):
        self.volume_name = volume_name
        self.mount_point = "/app/scan_folders"
        
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
            host_path = Path(host_path).resolve()
            
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
            
            logger.info(f"Mounting {host_path} to shared volume as {unique_folder_name}")
            
            # First, create the volume if it doesn't exist
            self._ensure_volume_exists()
            
            # Create a temporary container that mounts both the host path and the volume
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{host_path}:/source:ro",
                "-v", f"{self.volume_name}:/dest",
                "alpine:latest",
                "sh", "-c", f"mkdir -p /dest/{unique_folder_name} && cp -r /source/* /dest/{unique_folder_name}/"
            ]
            
            logger.info(f"Running: {' '.join(docker_cmd)}")
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully mounted {host_path} to shared volume as {unique_folder_name}")
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
                lines = result.stdout.strip().split('\n')
                folders = []
                for line in lines:
                    if line.startswith('d'):  # Directory
                        parts = line.split()
                        if len(parts) >= 9:
                            folder_name = parts[8]
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
    
    def get_folder_path(self, folder_name: str) -> str:
        """Get the path to a folder in the shared volume"""
        return f"{self.mount_point}/{folder_name}"
    
    def folder_exists(self, folder_name: str) -> bool:
        """Check if a folder exists in the shared volume"""
        try:
            container_name = f"volume-check-{folder_name}-{os.getpid()}"
            
            docker_cmd = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{self.volume_name}:/dest",
                "alpine:latest",
                "sh", "-c", f"test -d /dest/{folder_name}"
            ]
            
            result = subprocess.run(docker_cmd, capture_output=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error checking folder existence: {e}")
            return False
    
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

def main():
    parser = argparse.ArgumentParser(description="Volume Manager for Dynamic Folder Mounting")
    parser.add_argument("command", choices=["mount", "unmount", "list", "cleanup"], help="Command to execute")
    parser.add_argument("--path", help="Host path to mount (for mount command)")
    parser.add_argument("--name", help="Folder name in shared volume (for mount/unmount commands)")
    parser.add_argument("--volume", default="shared_scan_folders", help="Docker volume name")
    parser.add_argument("--max-age", type=int, default=24, help="Maximum age in hours for cleanup")
    
    args = parser.parse_args()
    
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