#!/usr/bin/env python3
"""
Check the file processing queue status
"""

import asyncio
import asyncpg
import yaml
from pathlib import Path

async def check_queue():
    """Check the file processing queue"""
    try:
        # Load config
        config_path = Path("/app/config/main.yaml")
        if not config_path.exists():
            config_path = Path(__file__).parent.parent / "config" / "main.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        postgres_config = config.get('core', {}).get('storage', {}).get('postgresql', {})
        
        # Connect to database
        conn = await asyncpg.connect(
            host=postgres_config.get('host', 'localhost'),
            port=postgres_config.get('port', 5432),
            database=postgres_config.get('database', 'mep_ainabox'),
            user=postgres_config.get('user', 'mep_user'),
            password=postgres_config.get('password', 'mep_password')
        )
        
        # Check queue items
        rows = await conn.fetch("""
            SELECT id, filename, status, file_path, parent_directory 
            FROM file_processing_queue 
            ORDER BY id DESC 
            LIMIT 10
        """)
        
        print("📋 File Processing Queue Status:")
        print("=" * 50)
        
        if not rows:
            print("ℹ️  No items in queue")
        else:
            for row in rows:
                print(f"  {row['id']}: {row['filename']} - {row['status']}")
                print(f"    Path: {row['file_path']}")
                print(f"    Parent: {row['parent_directory']}")
                print()
        
        # Check file_info table
        file_rows = await conn.fetch("""
            SELECT id, filename, file_path, parent_directory 
            FROM file_info 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        print("📁 File Info Table:")
        print("=" * 50)
        
        if not file_rows:
            print("ℹ️  No files in file_info table")
        else:
            for row in file_rows:
                print(f"  {row['id']}: {row['filename']}")
                print(f"    Path: {row['file_path']}")
                print(f"    Parent: {row['parent_directory']}")
                print()
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_queue()) 