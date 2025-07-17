#!/usr/bin/env python3
"""
File Watcher Demonstration Script
Shows how the file watcher automatically processes new files
"""

import asyncio
import httpx
import os
import time
from pathlib import Path
from datetime import datetime

# Configuration
FILE_WATCHER_URL = "http://localhost:8009"
WATCH_FOLDER = "./watch_folder"

def create_test_files():
    """Create various test files to demonstrate file watcher functionality"""
    print("📁 Creating test files...")
    
    os.makedirs(WATCH_FOLDER, exist_ok=True)
    
    # Test file 1: Simple text document
    text_file = os.path.join(WATCH_FOLDER, "sample_report.txt")
    with open(text_file, "w") as f:
        f.write("Sample Report\n")
        f.write("=" * 20 + "\n")
        f.write("This is a sample text document for testing the file watcher.\n")
        f.write("It contains basic text content that should be processed.\n")
        f.write(f"Created: {datetime.utcnow().isoformat()}\n")
    print(f"✅ Created: {text_file}")
    
    # Test file 2: CSV data file
    csv_file = os.path.join(WATCH_FOLDER, "financial_data.csv")
    with open(csv_file, "w") as f:
        f.write("Date,Revenue,Expenses,Profit\n")
        f.write("2024-01-01,10000,6000,4000\n")
        f.write("2024-01-02,12000,7000,5000\n")
        f.write("2024-01-03,11000,6500,4500\n")
    print(f"✅ Created: {csv_file}")
    
    # Test file 3: HTML document
    html_file = os.path.join(WATCH_FOLDER, "webpage.html")
    with open(html_file, "w") as f:
        f.write("<!DOCTYPE html>\n")
        f.write("<html><head><title>Test Page</title></head>\n")
        f.write("<body>\n")
        f.write("<h1>Test Document</h1>\n")
        f.write("<p>This is a test HTML document for the file watcher.</p>\n")
        f.write("<p>It should be processed as a text document.</p>\n")
        f.write("</body></html>\n")
    print(f"✅ Created: {html_file}")
    
    # Test file 4: Invalid file (should be rejected)
    invalid_file = os.path.join(WATCH_FOLDER, "invalid.xyz")
    with open(invalid_file, "w") as f:
        f.write("This file has an unsupported extension.\n")
    print(f"⚠️  Created (should be rejected): {invalid_file}")

async def monitor_processing():
    """Monitor the file processing status"""
    print("\n🔍 Monitoring file processing...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(10):  # Monitor for 10 seconds
            try:
                # Check status
                response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/status")
                if response.status_code == 200:
                    status = response.json()
                    print(f"Status: {status['status']} | "
                          f"Processed: {status['processed_files_count']} | "
                          f"Errors: {status['error_files_count']} | "
                          f"Processing: {status['currently_processing']}")
                
                # Check processed files
                response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/processed")
                if response.status_code == 200:
                    processed = response.json()
                    if processed['count'] > 0:
                        print(f"  📄 Processed files:")
                        for file_info in processed['processed_files']:
                            print(f"    - {Path(file_info['file_path']).name}")
                            if 'document_id' in file_info:
                                print(f"      Document ID: {file_info['document_id']}")
                
                # Check error files
                response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/errors")
                if response.status_code == 200:
                    errors = response.json()
                    if errors['count'] > 0:
                        print(f"  ❌ Error files:")
                        for error_info in errors['error_files']:
                            print(f"    - {Path(error_info['file_path']).name}: {error_info['error']}")
                
            except Exception as e:
                print(f"Error monitoring: {e}")
            
            await asyncio.sleep(1)

async def demonstrate_file_watcher():
    """Demonstrate the file watcher functionality"""
    print("🚀 File Watcher Demonstration")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check if file watcher is running
            print("\n1. Checking file watcher status...")
            response = await client.get(f"{FILE_WATCHER_URL}/health")
            if response.status_code != 200:
                print("❌ File watcher is not running. Please start the service first.")
                return
            
            print("✅ File watcher is running")
            
            # Start the file watcher if not already running
            print("\n2. Starting file watcher...")
            response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/start")
            if response.status_code == 200:
                print("✅ File watcher started")
            else:
                print("⚠️  File watcher may already be running")
            
            # Create test files
            print("\n3. Creating test files...")
            create_test_files()
            
            # Monitor processing
            print("\n4. Monitoring file processing...")
            await monitor_processing()
            
            # Show final results
            print("\n5. Final results:")
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/processed")
            if response.status_code == 200:
                processed = response.json()
                print(f"✅ Successfully processed: {processed['count']} files")
            
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/errors")
            if response.status_code == 200:
                errors = response.json()
                print(f"❌ Files with errors: {errors['count']} files")
            
            print("\n" + "=" * 50)
            print("🎉 Demonstration completed!")
            print("\n📋 Summary:")
            print("- Files placed in the watch folder are automatically detected")
            print("- Valid files are sent to the core processor for processing")
            print("- Processed files are moved to the processed folder")
            print("- Invalid files are moved to the error folder")
            print("- You can monitor the status via the API endpoints")
            
        except Exception as e:
            print(f"❌ Demonstration failed: {e}")

async def interactive_demo():
    """Interactive demonstration with user input"""
    print("🎮 Interactive File Watcher Demo")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check if file watcher is running
            response = await client.get(f"{FILE_WATCHER_URL}/health")
            if response.status_code != 200:
                print("❌ File watcher is not running. Please start the service first.")
                return
            
            # Start file watcher
            await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/start")
            
            while True:
                print("\nOptions:")
                print("1. Create a test file")
                print("2. Check processing status")
                print("3. View processed files")
                print("4. View error files")
                print("5. Clear history")
                print("6. Exit")
                
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == "1":
                    filename = input("Enter filename (e.g., test.txt): ").strip()
                    if filename:
                        file_path = os.path.join(WATCH_FOLDER, filename)
                        content = input("Enter file content: ").strip()
                        with open(file_path, "w") as f:
                            f.write(content)
                        print(f"✅ Created file: {file_path}")
                
                elif choice == "2":
                    response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/status")
                    if response.status_code == 200:
                        status = response.json()
                        print(f"Status: {status['status']}")
                        print(f"Processed files: {status['processed_files_count']}")
                        print(f"Error files: {status['error_files_count']}")
                        print(f"Currently processing: {status['currently_processing']}")
                
                elif choice == "3":
                    response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/processed")
                    if response.status_code == 200:
                        processed = response.json()
                        print(f"Processed files ({processed['count']}):")
                        for file_info in processed['processed_files']:
                            print(f"  - {Path(file_info['file_path']).name}")
                
                elif choice == "4":
                    response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/errors")
                    if response.status_code == 200:
                        errors = response.json()
                        print(f"Error files ({errors['count']}):")
                        for error_info in errors['error_files']:
                            print(f"  - {Path(error_info['file_path']).name}: {error_info['error']}")
                
                elif choice == "5":
                    response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/clear-history")
                    if response.status_code == 200:
                        print("✅ History cleared")
                
                elif choice == "6":
                    break
                
                else:
                    print("Invalid choice. Please try again.")
                
                await asyncio.sleep(1)
            
            print("👋 Goodbye!")
            
        except Exception as e:
            print(f"❌ Interactive demo failed: {e}")

async def main():
    """Main function"""
    print("Choose demonstration mode:")
    print("1. Automatic demo (creates test files and monitors)")
    print("2. Interactive demo (manual file creation)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        await demonstrate_file_watcher()
    elif choice == "2":
        await interactive_demo()
    else:
        print("Invalid choice. Running automatic demo...")
        await demonstrate_file_watcher()

if __name__ == "__main__":
    asyncio.run(main()) 