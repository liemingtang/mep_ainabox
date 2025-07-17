#!/usr/bin/env python3
"""
Test script for the File Watcher service
"""

import asyncio
import httpx
import os
import time
import json
from pathlib import Path
from datetime import datetime

# Configuration
FILE_WATCHER_URL = "http://localhost:8009"
WATCH_FOLDER = "./watch_folder"
TEST_FILES = [
    "test_document.txt",
    "sample_report.pdf",
    "data.csv"
]

async def test_file_watcher():
    """Test the file watcher functionality"""
    print("🧪 Testing File Watcher Service")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Health check
            print("\n1. Testing health check...")
            response = await client.get(f"{FILE_WATCHER_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return
            
            # Test 2: Get service info
            print("\n2. Getting service info...")
            response = await client.get(f"{FILE_WATCHER_URL}/")
            if response.status_code == 200:
                info = response.json()
                print(f"✅ Service info: {info['message']} v{info['version']}")
                print(f"   Watch paths: {info['watch_paths']}")
                print(f"   Supported extensions: {len(info['supported_extensions'])}")
            else:
                print(f"❌ Failed to get service info: {response.status_code}")
                return
            
            # Test 3: Start file watcher
            print("\n3. Starting file watcher...")
            response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/start")
            if response.status_code == 200:
                start_data = response.json()
                print(f"✅ File watcher started: {start_data}")
            else:
                print(f"❌ Failed to start file watcher: {response.status_code} - {response.text}")
                return
            
            # Test 4: Check watcher status
            print("\n4. Checking watcher status...")
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Watcher status: {status['status']}")
                print(f"   Is alive: {status['is_alive']}")
                print(f"   Processed files: {status['processed_files_count']}")
                print(f"   Error files: {status['error_files_count']}")
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                return
            
            # Test 5: Create test files
            print("\n5. Creating test files...")
            os.makedirs(WATCH_FOLDER, exist_ok=True)
            
            # Create a simple text file
            test_file_path = os.path.join(WATCH_FOLDER, "test_document.txt")
            with open(test_file_path, "w") as f:
                f.write("This is a test document for the file watcher.\n")
                f.write("It should be automatically processed when detected.\n")
                f.write(f"Created at: {datetime.utcnow().isoformat()}\n")
            
            print(f"✅ Created test file: {test_file_path}")
            
            # Test 6: Wait for processing
            print("\n6. Waiting for file processing...")
            await asyncio.sleep(5)  # Wait for file to be processed
            
            # Test 7: Check processing results
            print("\n7. Checking processing results...")
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/processed")
            if response.status_code == 200:
                processed = response.json()
                print(f"✅ Processed files: {processed['count']}")
                for file_info in processed['processed_files']:
                    print(f"   - {file_info['file_path']} (processed at {file_info['processed_at']})")
            else:
                print(f"❌ Failed to get processed files: {response.status_code}")
            
            # Test 8: Check error files
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/errors")
            if response.status_code == 200:
                errors = response.json()
                print(f"✅ Error files: {errors['count']}")
                for error_info in errors['error_files']:
                    print(f"   - {error_info['file_path']} (error: {error_info['error']})")
            else:
                print(f"❌ Failed to get error files: {response.status_code}")
            
            # Test 9: Check updated status
            print("\n8. Checking updated status...")
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Updated status:")
                print(f"   Processed files: {status['processed_files_count']}")
                print(f"   Error files: {status['error_files_count']}")
                print(f"   Last activity: {status['last_activity']}")
                print(f"   Currently processing: {status['currently_processing']}")
            else:
                print(f"❌ Failed to get updated status: {response.status_code}")
            
            # Test 10: Test manual file processing
            print("\n9. Testing manual file processing...")
            manual_test_file = os.path.join(WATCH_FOLDER, "manual_test.txt")
            with open(manual_test_file, "w") as f:
                f.write("Manual test file for processing.\n")
            
            response = await client.post(
                f"{FILE_WATCHER_URL}/api/v1/watch/process-file",
                params={"file_path": manual_test_file}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Manual processing initiated: {result}")
            else:
                print(f"❌ Manual processing failed: {response.status_code} - {response.text}")
            
            # Test 11: Test invalid file
            print("\n10. Testing invalid file handling...")
            invalid_file = os.path.join(WATCH_FOLDER, "invalid.xyz")
            with open(invalid_file, "w") as f:
                f.write("This file has an unsupported extension.\n")
            
            await asyncio.sleep(3)  # Wait for processing
            
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/errors")
            if response.status_code == 200:
                errors = response.json()
                print(f"✅ Invalid file handling: {errors['count']} error files")
            else:
                print(f"❌ Failed to check error files: {response.status_code}")
            
            # Test 12: Stop file watcher
            print("\n11. Stopping file watcher...")
            response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/stop")
            if response.status_code == 200:
                stop_data = response.json()
                print(f"✅ File watcher stopped: {stop_data}")
            else:
                print(f"❌ Failed to stop file watcher: {response.status_code} - {response.text}")
            
            print("\n" + "=" * 50)
            print("🎉 File Watcher testing completed!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            raise

async def test_file_watcher_integration():
    """Test file watcher integration with core processor"""
    print("\n🔗 Testing File Watcher Integration")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check if core processor is available
            print("\n1. Checking core processor availability...")
            try:
                response = await client.get("http://localhost:8001/health")
                if response.status_code == 200:
                    print("✅ Core processor is available")
                else:
                    print("⚠️  Core processor health check failed")
                    return
            except Exception as e:
                print(f"⚠️  Core processor not available: {e}")
                print("   Skipping integration test")
                return
            
            # Start file watcher
            print("\n2. Starting file watcher for integration test...")
            response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/start")
            if response.status_code != 200:
                print(f"❌ Failed to start file watcher: {response.status_code}")
                return
            
            # Create a test file that should be processed
            print("\n3. Creating test file for processing...")
            test_file = os.path.join(WATCH_FOLDER, "integration_test.txt")
            with open(test_file, "w") as f:
                f.write("Integration test document.\n")
                f.write("This file should be processed by the core processor.\n")
                f.write(f"Created at: {datetime.utcnow().isoformat()}\n")
            
            print(f"✅ Created integration test file: {test_file}")
            
            # Wait for processing
            print("\n4. Waiting for processing...")
            await asyncio.sleep(10)
            
            # Check if file was processed
            print("\n5. Checking processing results...")
            response = await client.get(f"{FILE_WATCHER_URL}/api/v1/watch/processed")
            if response.status_code == 200:
                processed = response.json()
                if processed['count'] > 0:
                    print(f"✅ Integration test successful: {processed['count']} files processed")
                    for file_info in processed['processed_files']:
                        if "integration_test" in file_info['file_path']:
                            print(f"   - Integration test file processed successfully")
                            if 'document_id' in file_info:
                                print(f"   - Document ID: {file_info['document_id']}")
                else:
                    print("⚠️  No files were processed during integration test")
            else:
                print(f"❌ Failed to check processing results: {response.status_code}")
            
            # Stop file watcher
            print("\n6. Stopping file watcher...")
            response = await client.post(f"{FILE_WATCHER_URL}/api/v1/watch/stop")
            if response.status_code == 200:
                print("✅ File watcher stopped")
            
            print("\n" + "=" * 50)
            print("🎉 Integration testing completed!")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            raise

async def main():
    """Main test function"""
    print("🚀 Starting File Watcher Tests")
    print("=" * 50)
    
    # Test basic functionality
    await test_file_watcher()
    
    # Test integration with core processor
    await test_file_watcher_integration()
    
    print("\n✨ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 