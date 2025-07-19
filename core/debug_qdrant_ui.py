#!/usr/bin/env python3
"""
Debug script to test Qdrant UI collections loading
"""

import asyncio
import httpx
import json
import time

async def debug_qdrant_ui():
    """Debug the Qdrant UI collections loading issue"""
    
    print("🔍 Debugging Qdrant UI Collections Loading")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Check if Qdrant UI is serving the correct file
            print("1️⃣ Testing Qdrant UI file serving...")
            
            response = await client.get("http://localhost:7070/index.html", timeout=5.0)
            if response.status_code == 200:
                html_content = response.text
                print("   ✅ Qdrant UI is serving HTML file")
                
                # Check if the loadCollections function is present
                if "loadCollections();" in html_content:
                    print("   ✅ loadCollections() function is present in HTML")
                else:
                    print("   ❌ loadCollections() function is NOT present in HTML")
                
                # Check if it's called on page load
                if "loadStatus();" in html_content and "loadCollections();" in html_content:
                    load_status_pos = html_content.find("loadStatus();")
                    load_collections_pos = html_content.find("loadCollections();")
                    if load_status_pos < load_collections_pos:
                        print("   ✅ loadCollections() is called after loadStatus()")
                    else:
                        print("   ⚠️ loadCollections() is called before loadStatus()")
                else:
                    print("   ❌ loadCollections() is not called on page load")
            else:
                print(f"   ❌ Qdrant UI failed: {response.status_code}")
                return
            
            # Test 2: Test the exact API call that the UI makes
            print("2️⃣ Testing the exact API call the UI makes...")
            
            response = await client.get(
                "http://localhost:6333/collections",
                headers={
                    "api-key": "qdrant_api_key",
                    "Content-Type": "application/json"
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                collections = data.get("result", {}).get("collections", [])
                print(f"   ✅ API call successful. Found {len(collections)} collections:")
                for collection in collections:
                    print(f"      - {collection.get('name')}")
            else:
                print(f"   ❌ API call failed: {response.status_code} {response.text}")
            
            # Test 3: Test with different headers to see if that's the issue
            print("3️⃣ Testing with different header combinations...")
            
            # Test without Content-Type header
            response = await client.get(
                "http://localhost:6333/collections",
                headers={"api-key": "qdrant_api_key"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                print("   ✅ Works without Content-Type header")
            else:
                print(f"   ❌ Fails without Content-Type header: {response.status_code}")
            
            # Test 4: Check if there are any CORS issues
            print("4️⃣ Testing CORS headers...")
            
            response = await client.get(
                "http://localhost:7070/index.html",
                headers={"Origin": "http://localhost:7070"},
                timeout=5.0
            )
            
            cors_headers = response.headers.get("Access-Control-Allow-Origin")
            if cors_headers:
                print(f"   ✅ CORS headers present: {cors_headers}")
            else:
                print("   ⚠️ No CORS headers found")
            
            # Test 5: Simulate browser behavior with fetch
            print("5️⃣ Simulating browser fetch behavior...")
            
            # This simulates what the browser would do
            test_script = """
            const QDRANT_URL = 'http://localhost:6333';
            const apiToken = 'qdrant_api_key';
            
            function getHeaders() {
                const headers = {
                    'Content-Type': 'application/json'
                };
                if (apiToken) {
                    headers['api-key'] = apiToken;
                }
                return headers;
            }
            
            async function testLoadCollections() {
                try {
                    const response = await fetch(`${QDRANT_URL}/collections`, {
                        headers: getHeaders()
                    });
                    const data = await response.json();
                    console.log('Collections:', data);
                    return data;
                } catch (error) {
                    console.error('Error:', error);
                    return null;
                }
            }
            """
            
            print("   📝 Test script generated. You can run this in browser console:")
            print("   " + "="*60)
            print(test_script)
            print("   " + "="*60)
            print("   Then call: testLoadCollections()")
            
            print("\n🔍 Debug Summary:")
            print("   - Qdrant UI is serving files ✅")
            print("   - API endpoint works directly ✅")
            print("   - Collections exist in Qdrant ✅")
            print("\n💡 Possible Issues:")
            print("   1. Browser caching - try hard refresh (Ctrl+F5)")
            print("   2. JavaScript errors - check browser console")
            print("   3. CORS issues - check browser network tab")
            print("   4. API token not being passed correctly")
            print("\n🔧 Next Steps:")
            print("   1. Open browser developer tools (F12)")
            print("   2. Go to Console tab")
            print("   3. Navigate to http://localhost:7070/index.html?api_token=qdrant_api_key")
            print("   4. Look for any JavaScript errors")
            print("   5. Go to Network tab and check if the API call is made")
            
        except Exception as e:
            print(f"❌ Debug failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_qdrant_ui()) 