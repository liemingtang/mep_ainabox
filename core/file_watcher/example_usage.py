#!/usr/bin/env python3
"""
Example usage of the Folder Scanner Utility

This script demonstrates how to use the folder scanner in your own Python code.
"""

import asyncio
import os
from pathlib import Path
from folder_scanner import FolderScanner

async def example_basic_usage():
    """Example of basic folder scanning"""
    print("=== Basic Folder Scanning ===")
    
    # Create a scanner instance
    scanner = FolderScanner(dry_run=True)  # Use dry_run=True for testing
    
    # Scan and process a folder
    folder_path = "/path/to/your/documents"  # Replace with actual path
    
    if os.path.exists(folder_path):
        await scanner.process_folder(
            folder_path=folder_path,
            recursive=True,  # Scan subdirectories
            max_depth=None,  # No depth limit
            concurrent_limit=5  # Process 5 files at once
        )
        
        # Access results
        print(f"Processed: {len(scanner.processed_files)} files")
        print(f"Errors: {len(scanner.error_files)} files")
        print(f"Skipped: {len(scanner.skipped_files)} files")
    else:
        print(f"Folder {folder_path} does not exist")

async def example_custom_scanning():
    """Example of custom scanning options"""
    print("\n=== Custom Scanning Options ===")
    
    scanner = FolderScanner(dry_run=True)
    
    # Scan only top-level files (no subdirectories)
    await scanner.process_folder(
        folder_path="/path/to/folder",
        recursive=False,
        concurrent_limit=3
    )
    
    # Scan with depth limit
    await scanner.process_folder(
        folder_path="/path/to/folder",
        recursive=True,
        max_depth=2,  # Only scan 2 levels deep
        concurrent_limit=10
    )

def example_scan_only():
    """Example of scanning without processing"""
    print("\n=== Scan Only (No Processing) ===")
    
    scanner = FolderScanner()
    
    # Just scan and get the list of files
    files_to_process = scanner.scan_folder(
        folder_path="/path/to/folder",
        recursive=True,
        max_depth=3
    )
    
    print(f"Found {len(files_to_process)} files to process:")
    for file_path in files_to_process:
        print(f"  - {file_path}")

async def example_batch_processing():
    """Example of processing multiple folders"""
    print("\n=== Batch Processing Multiple Folders ===")
    
    folders = [
        "/path/to/documents",
        "/path/to/images", 
        "/path/to/spreadsheets"
    ]
    
    scanner = FolderScanner(dry_run=True)
    
    for folder in folders:
        if os.path.exists(folder):
            print(f"\nProcessing folder: {folder}")
            await scanner.process_folder(folder, recursive=True)
            
            # Print summary for this folder
            print(f"  Processed: {len(scanner.processed_files)}")
            print(f"  Errors: {len(scanner.error_files)}")
            print(f"  Skipped: {len(scanner.skipped_files)}")
        else:
            print(f"Folder {folder} does not exist")

async def example_with_error_handling():
    """Example with comprehensive error handling"""
    print("\n=== Error Handling Example ===")
    
    try:
        scanner = FolderScanner(dry_run=True)
        
        # Process folder with error handling
        await scanner.process_folder(
            folder_path="/path/to/folder",
            recursive=True,
            concurrent_limit=5
        )
        
        # Check for errors
        if scanner.error_files:
            print("Some files had processing errors:")
            for error_file in scanner.error_files:
                print(f"  - {error_file['file_path']}: {error_file['error']}")
        
        # Save detailed report
        scanner.save_report("processing_report.json")
        print("Detailed report saved to processing_report.json")
        
    except Exception as e:
        print(f"Error during processing: {e}")

def example_integration_with_existing_code():
    """Example of integrating with existing code"""
    print("\n=== Integration Example ===")
    
    # Example: Process files based on some condition
    def should_process_file(file_path):
        """Custom logic to decide if a file should be processed"""
        path = Path(file_path)
        
        # Only process files modified in the last 7 days
        import time
        file_age = time.time() - path.stat().st_mtime
        days_old = file_age / (24 * 3600)
        
        return days_old <= 7
    
    async def process_recent_files():
        scanner = FolderScanner(dry_run=True)
        
        # Scan folder
        all_files = scanner.scan_folder("/path/to/folder", recursive=True)
        
        # Filter files based on custom logic
        recent_files = [f for f in all_files if should_process_file(f)]
        
        print(f"Found {len(recent_files)} recent files to process")
        
        # Process only recent files
        for file_path in recent_files:
            await scanner.process_document(file_path, "/path/to/folder")
        
        return scanner

async def main():
    """Main function demonstrating all examples"""
    print("Folder Scanner Utility - Usage Examples")
    print("="*50)
    
    # Note: These examples use dry_run=True to avoid actually processing files
    # Remove dry_run=True when you want to actually process files
    
    # Basic usage
    await example_basic_usage()
    
    # Custom scanning
    await example_custom_scanning()
    
    # Scan only
    example_scan_only()
    
    # Batch processing
    await example_batch_processing()
    
    # Error handling
    await example_with_error_handling()
    
    # Integration example
    await example_integration_with_existing_code()
    
    print("\n" + "="*50)
    print("All examples completed!")
    print("Remember to:")
    print("1. Replace '/path/to/folder' with actual paths")
    print("2. Set dry_run=False when you want to actually process files")
    print("3. Ensure the core processor service is running")
    print("4. Check file permissions and disk space")

if __name__ == "__main__":
    # Run the examples
    asyncio.run(main()) 