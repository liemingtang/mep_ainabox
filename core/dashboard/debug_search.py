#!/usr/bin/env python3
"""
Debug script to test text-based search logic
"""

import asyncio
import httpx
import json

async def debug_search():
    """Debug the text-based search logic"""
    
    qdrant_url = "http://localhost:6333"
    qdrant_api_key = "qdrant_api_key"
    query = "finland"  # Search for a term that should be in the content
    
    print(f"🔍 Debugging search for query: '{query}'")
    
    # Get documents from Qdrant
    scroll_payload = {
        "limit": 100,  # Get more documents like the LLM search
        "with_payload": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            qdrant_resp = await client.post(
                f"{qdrant_url}/collections/documents/points/scroll",
                headers={"api-key": qdrant_api_key, "Content-Type": "application/json"},
                json=scroll_payload
            )
            qdrant_resp.raise_for_status()
            all_docs = qdrant_resp.json().get("result", {}).get("points", [])
            
            print(f"📄 Retrieved {len(all_docs)} documents")
            
            # Test text-based filtering
            query_lower = query.lower()
            print(f"🔎 Searching for: '{query_lower}'")
            
            filtered_docs = []
            for i, doc in enumerate(all_docs):
                content = doc.get("payload", {}).get("content", "").lower()
                print(f"  Document {i}: content length = {len(content)}")
                print(f"    Preview: {content[:100]}...")
                
                if query_lower in content:
                    score = content.count(query_lower) / len(content) if content else 0
                    filtered_docs.append({
                        **doc,
                        "score": score
                    })
                    print(f"    ✅ MATCH FOUND! Score: {score:.4f}")
                else:
                    print(f"    ❌ No match")
                print()
            
            print(f"🎯 Found {len(filtered_docs)} matching documents")
            
            # Show top results
            if filtered_docs:
                sorted_results = sorted(filtered_docs, key=lambda x: x.get("score", 0), reverse=True)
                for i, result in enumerate(sorted_results[:3]):
                    content = result.get("payload", {}).get("content", "")
                    score = result.get("score", 0)
                    print(f"  Top result {i+1}:")
                    print(f"    Score: {score:.4f}")
                    print(f"    Content: {content[:200]}...")
                    print()
            else:
                print("❌ No matching documents found")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_search())
