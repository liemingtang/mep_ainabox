#!/usr/bin/env python3
"""
Single File Text Processor - Extract text from a single file
Used by batch processing to extract text from individual files
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Redirect logging to stderr
)
logger = logging.getLogger(__name__)

# Supported text file extensions
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
    '.py', '.js', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs', '.swift', '.kt',
    '.log', '.out', '.err', '.conf', '.cfg', '.ini', '.yaml', '.yml'
}

def extract_text_from_file(file_path: Path) -> Dict[str, Any]:
    """Extract text from a single file"""
    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        file_extension = file_path.suffix.lower()
        
        # Handle different file types
        if file_extension in SUPPORTED_EXTENSIONS:
            # Text-based files - read directly
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "success": True,
                "text_content": content,
                "text_length": len(content),
                "quality_score": min(1.0, len(content) / 1000.0),
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size
            }
        else:
            # For other file types, try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "success": True,
                    "text_content": content,
                    "text_length": len(content),
                    "quality_score": min(1.0, len(content) / 1000.0),
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size
                }
            except UnicodeDecodeError:
                # If UTF-8 fails, try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        return {
                            "success": True,
                            "text_content": content,
                            "text_length": len(content),
                            "quality_score": min(1.0, len(content) / 1000.0),
                            "file_path": str(file_path),
                            "file_size": file_path.stat().st_size
                        }
                    except UnicodeDecodeError:
                        continue
                
                # If all encodings fail, return a placeholder
                return {
                    "success": True,
                    "text_content": f"[Binary or unsupported file type: {file_extension}]",
                    "text_length": 0,
                    "quality_score": 0.0,
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size
                }
    
    except Exception as e:
        logger.error(f"❌ Failed to process text file {file_path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": str(file_path),
            "text_content": "",
            "text_length": 0,
            "quality_score": 0.0
        }

def main():
    """Main function for single file processing"""
    parser = argparse.ArgumentParser(description="Single File Text Processor")
    parser.add_argument("file_path", help="Path to file to process")
    parser.add_argument("--output-format", choices=["json", "text"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Process the file
    file_path = Path(args.file_path)
    result = extract_text_from_file(file_path)
    
    # Output result
    if args.output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Text output format
        if result["success"]:
            print(f"✅ Successfully processed: {result['file_path']}")
            print(f"Text length: {result['text_length']} characters")
            print(f"File size: {result['file_size']} bytes")
            print(f"Quality score: {result['quality_score']:.2f}")
            print("\n" + "="*50)
            print("TEXT CONTENT:")
            print("="*50)
            print(result["text_content"])
        else:
            print(f"❌ Failed to process: {result['file_path']}")
            print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
