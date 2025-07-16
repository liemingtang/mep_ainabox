#!/usr/bin/env python3
"""
Test script for the Core System
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import httpx


class CoreSystemTester:
    """Test the core system functionality"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.core_url = "http://localhost:8001"
        self.timeout = 30.0
    
    async def test_health_checks(self) -> bool:
        """Test health checks for all services"""
        print("🔍 Testing health checks...")
        
        services = [
            ("API Gateway", f"{self.base_url}/health"),
            ("Core Processor", f"{self.core_url}/health"),
        ]
        
        all_healthy = True
        for service_name, url in services:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"✅ {service_name}: Healthy")
                    else:
                        print(f"❌ {service_name}: Unhealthy (Status: {response.status_code})")
                        all_healthy = False
            except Exception as e:
                print(f"❌ {service_name}: Error - {e}")
                all_healthy = False
        
        return all_healthy
    
    async def test_metrics_endpoints(self) -> bool:
        """Test metrics endpoints"""
        print("\n📊 Testing metrics endpoints...")
        
        services = [
            ("API Gateway", f"{self.base_url}/metrics"),
            ("Core Processor", f"{self.core_url}/metrics"),
        ]
        
        all_working = True
        for service_name, url in services:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"✅ {service_name}: Metrics available")
                    else:
                        print(f"❌ {service_name}: Metrics failed (Status: {response.status_code})")
                        all_working = False
            except Exception as e:
                print(f"❌ {service_name}: Metrics error - {e}")
                all_working = False
        
        return all_working
    
    async def test_document_upload(self) -> bool:
        """Test document upload functionality"""
        print("\n📄 Testing document upload...")
        
        # Create a test document with unique content
        test_doc_path = Path("test_document.txt")
        import time
        timestamp = int(time.time())
        test_content = f"This is a test document for the MDIS system (timestamp: {timestamp}).\nIt contains some sample text for testing purposes."
        
        try:
            with open(test_doc_path, "w") as f:
                f.write(test_content)
            
            # Generate unique file hash
            file_hash = hashlib.sha256(test_content.encode()).hexdigest()
            
            # Test document upload
            document_data = {
                "filename": "test_document.txt",
                "file_path": str(test_doc_path.absolute()),
                "file_size": len(test_content),
                "mime_type": "text/plain",
                "file_hash": file_hash,
                "source": "test",
                "document_type": "txt",
                "company": "Test Company",
                "year": 2024,
                "metadata": {
                    "test_key": "test_value",
                    "upload_source": "test_script",
                    "content_length": len(test_content)
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.core_url}/documents/upload",
                    json=document_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Document upload successful: {result.get('document_id')}")
                    
                    # Test getting document
                    doc_id = result.get('document_id')
                    if doc_id:
                        doc_response = await client.get(f"{self.core_url}/documents/{doc_id}")
                        if doc_response.status_code == 200:
                            print(f"✅ Document retrieval successful")
                            return True
                        else:
                            print(f"❌ Document retrieval failed: {doc_response.status_code}")
                            return False
                    else:
                        print("❌ No document ID returned")
                        return False
                else:
                    print(f"❌ Document upload failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Document upload error: {e}")
            return False
        finally:
            # Clean up test file
            if test_doc_path.exists():
                test_doc_path.unlink()
    
    async def test_system_stats(self) -> bool:
        """Test system statistics endpoint"""
        print("\n📈 Testing system statistics...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.core_url}/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    print(f"✅ System stats retrieved:")
                    print(f"   - Total documents: {stats.get('total_documents', 0)}")
                    print(f"   - Documents by status: {stats.get('documents_by_status', {})}")
                    return True
                else:
                    print(f"❌ System stats failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ System stats error: {e}")
            return False
    
    async def test_list_documents(self) -> bool:
        """Test document listing"""
        print("\n📋 Testing document listing...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.core_url}/documents?limit=10")
                
                if response.status_code == 200:
                    documents = response.json()
                    print(f"✅ Document listing successful: {len(documents)} documents")
                    return True
                else:
                    print(f"❌ Document listing failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Document listing error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Core System Tests")
        print("=" * 50)
        
        tests = [
            ("Health Checks", self.test_health_checks),
            ("Metrics Endpoints", self.test_metrics_endpoints),
            ("Document Upload", self.test_document_upload),
            ("System Statistics", self.test_system_stats),
            ("Document Listing", self.test_list_documents),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name}: Test error - {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Core system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the system configuration.")
            return False


async def main():
    """Main test function"""
    tester = CoreSystemTester()
    
    # Wait a bit for services to be ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(5)
    
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Core system is ready for use!")
        sys.exit(0)
    else:
        print("\n❌ Core system has issues that need to be resolved.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 