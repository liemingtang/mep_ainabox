#!/usr/bin/env python3
"""
Debug script to test service endpoints and see what's happening with configuration and logs
"""

import asyncio
import httpx
import json
import subprocess
from datetime import datetime

# Dashboard URL
DASHBOARD_URL = "http://localhost:8010"

async def test_service_endpoint(service_name):
    """Test a specific service endpoint"""
    print(f"\n🔍 Testing {service_name} service:")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test service detail endpoint
            print(f"Testing /api/service/{service_name}")
            response = await client.get(f"{DASHBOARD_URL}/api/service/{service_name}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Service status: {data.get('status', 'unknown')}")
                print(f"✅ Configuration items: {len(data.get('configuration', []))}")
                print(f"✅ Log lines: {len(data.get('logs', []))}")
                print(f"✅ Metrics keys: {list(data.get('metrics', {}).keys())}")
                
                # Show first few configuration items
                config = data.get('configuration', [])
                if config:
                    print(f"\n📋 Configuration items:")
                    for i, item in enumerate(config[:3]):
                        print(f"   {i+1}. {item.get('key', 'N/A')}: {item.get('value', 'N/A')[:50]}...")
                    if len(config) > 3:
                        print(f"   ... and {len(config) - 3} more")
                else:
                    print("   No configuration items found")
                
                # Show first few log lines
                logs = data.get('logs', [])
                if logs:
                    print(f"\n📋 Log lines:")
                    for i, log in enumerate(logs[:3]):
                        print(f"   {i+1}. {log.strip()[:100]}...")
                    if len(logs) > 3:
                        print(f"   ... and {len(logs) - 3} more")
                else:
                    print("   No log lines found")
                
                return True
            else:
                print(f"❌ Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

async def test_individual_endpoints(service_name):
    """Test individual endpoints for a service"""
    print(f"\n🔧 Testing individual endpoints for {service_name}:")
    print("=" * 50)
    
    endpoints = [
        f"/api/service/{service_name}/configuration",
        f"/api/service/{service_name}/logs?lines=10",
        f"/api/service/{service_name}/metrics"
    ]
    
    for endpoint in endpoints:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                print(f"\nTesting {endpoint}")
                response = await client.get(f"{DASHBOARD_URL}{endpoint}")
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if 'configuration' in endpoint:
                        config = data.get('configuration', [])
                        print(f"✅ Configuration: {len(config)} items")
                        if config:
                            print(f"   Sample: {config[0].get('key', 'N/A')}")
                    elif 'logs' in endpoint:
                        logs = data.get('logs', [])
                        print(f"✅ Logs: {len(logs)} lines")
                        if logs:
                            print(f"   Sample: {logs[0].strip()[:100]}...")
                    elif 'metrics' in endpoint:
                        metrics = data.get('metrics', {})
                        print(f"✅ Metrics: {list(metrics.keys())}")
                else:
                    print(f"❌ Error: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"Error details: {error_data}")
                    except:
                        print(f"Error text: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

async def test_docker_access():
    """Test if Docker access is working"""
    print(f"\n🐳 Testing Docker access:")
    print("=" * 50)
    
    try:
        # Test if dashboard container can access Docker
        result = subprocess.run(
            ["docker", "exec", "mep-dashboard", "docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            print(f"✅ Dashboard can access Docker. Found {len(containers)} containers:")
            for container in containers[:5]:
                if container:
                    print(f"   - {container}")
            return True
        else:
            print(f"❌ Dashboard cannot access Docker: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Docker access: {e}")
        return False

async def test_service_connectivity():
    """Test if dashboard can connect to services"""
    print(f"\n🌐 Testing service connectivity:")
    print("=" * 50)
    
    services = [
        ("file-watcher", "http://localhost:8009/health"),
        ("core-processor", "http://localhost:8001/health"),
        ("elasticsearch", "http://localhost:9200/_cluster/health")
    ]
    
    for service_name, url in services:
        try:
            # Test from inside dashboard container
            result = subprocess.run(
                ["docker", "exec", "mep-dashboard", "curl", "-f", url],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ {service_name}: Accessible")
            else:
                print(f"❌ {service_name}: Not accessible ({result.stderr.strip()})")
        except Exception as e:
            print(f"❌ {service_name}: Error testing ({e})")

async def main():
    """Main debug function"""
    print("🚀 MDIS Dashboard Debug Suite")
    print("=" * 50)
    print(f"Testing dashboard at: {DASHBOARD_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test Docker access
    await test_docker_access()
    
    # Test service connectivity
    await test_service_connectivity()
    
    # Test file-watcher service
    await test_service_endpoint("file-watcher")
    
    # Test individual endpoints
    await test_individual_endpoints("file-watcher")
    
    print("\n✅ Debug suite completed!")

if __name__ == "__main__":
    asyncio.run(main()) 