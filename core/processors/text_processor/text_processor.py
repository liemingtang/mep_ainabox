#!/usr/bin/env python3
"""
Dynamic Text Processor - Extract text from files in any folder
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Redirect logging to stderr
)
logger = logging.getLogger(__name__)

# Configuration
PROCESSING_PIPELINE_URL = os.getenv("PROCESSING_PIPELINE_URL", "http://localhost:8003")
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
    '.py', '.js', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs', '.swift', '.kt',
    '.log', '.out', '.err', '.conf', '.cfg', '.ini', '.yaml', '.yml'
}

class TextProcessor:
    """Dynamic text processor for extracting text from files"""
    
    def __init__(self, pipeline_url: str = PROCESSING_PIPELINE_URL):
        self.pipeline_url = pipeline_url
        self.processed_files = []
        self.error_files = []
        self.skipped_files = []
        
    def extract_text_from_file(self, file_path: Path) -> Dict[str, Any]:
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
            logger.error(f"Error extracting text from {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": str(file_path)
            }
    
    def find_files(self, folder_path: Path, recursive: bool = True, max_depth: Optional[int] = None) -> List[Path]:
        """Find all files in the folder"""
        files = []
        
        if recursive:
            if max_depth is not None:
                for depth in range(max_depth + 1):
                    pattern = "*/" * depth + "*"
                    files.extend(folder_path.glob(pattern))
            else:
                files = list(folder_path.rglob("*"))
        else:
            files = list(folder_path.glob("*"))
        
        # Filter for files only (not directories) and supported extensions
        files = [f for f in files if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
        
        return files
    
    async def process_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """Process a single file"""
        try:
            logger.info(f"Processing file: {file_path}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would extract text from: {file_path}")
                return {
                    "success": True,
                    "file_path": str(file_path),
                    "dry_run": True
                }
            
            # Extract text from file
            result = self.extract_text_from_file(file_path)
            
            if result["success"]:
                logger.info(f"Successfully extracted {result['text_length']} characters from {file_path}")
                self.processed_files.append(str(file_path))
            else:
                logger.error(f"Failed to extract text from {file_path}: {result.get('error', 'Unknown error')}")
                self.error_files.append(str(file_path))
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.error_files.append(str(file_path))
            return {
                "success": False,
                "error": str(e),
                "file_path": str(file_path)
            }
    
    async def process_files_concurrent(self, files: List[Path], concurrent: int = 5, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Process files concurrently"""
        semaphore = asyncio.Semaphore(concurrent)
        
        async def process_with_semaphore(file_path: Path) -> Dict[str, Any]:
            async with semaphore:
                return await self.process_file(file_path, dry_run)
        
        tasks = [process_with_semaphore(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                processed_results.append({
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def generate_report(self, results: List[Dict[str, Any]], output_format: str = "json") -> str:
        """Generate processing report"""
        total_files = len(results)
        successful_files = len([r for r in results if r.get("success", False)])
        error_files = total_files - successful_files
        
        if output_format == "summary":
            return f"""
============================================================
TEXT EXTRACTION SUMMARY
============================================================
Total files: {total_files}
Successful extractions: {successful_files}
Failed extractions: {error_files}
Average text length: {sum(r.get('text_length', 0) for r in results if r.get('success', False)) / max(successful_files, 1):.0f} characters
============================================================
"""
        elif output_format == "text":
            report = f"Text Extraction Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"Total files: {total_files}\n"
            report += f"Successful: {successful_files}\n"
            report += f"Failed: {error_files}\n\n"
            
            for result in results:
                if result.get("success", False):
                    report += f"✅ {result.get('file_path', 'N/A')}: {result.get('text_length', 0)} chars\n"
                else:
                    report += f"❌ {result.get('file_path', 'N/A')}: {result.get('error', 'Unknown error')}\n"
            
            return report
        else:  # json
            return json.dumps({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_files": total_files,
                    "successful_files": successful_files,
                    "error_files": error_files,
                    "average_text_length": sum(r.get('text_length', 0) for r in results if r.get('success', False)) / max(successful_files, 1)
                },
                "results": results
            }, indent=2)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Dynamic Text Processor")
    parser.add_argument("folder_path", help="Path to folder to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without actually doing it")
    parser.add_argument("--recursive", action="store_true", default=True, help="Process subdirectories recursively")
    parser.add_argument("--no-recursive", action="store_true", help="Don't process subdirectories")
    parser.add_argument("--max-depth", type=int, help="Maximum directory depth to scan")
    parser.add_argument("--concurrent", type=int, default=5, help="Number of concurrent processing jobs")
    parser.add_argument("--output", choices=["json", "text", "summary"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Determine recursive setting
    recursive = args.recursive and not args.no_recursive
    
    # Initialize processor
    processor = TextProcessor()
    
    # Find files
    folder_path = Path(args.folder_path)
    if not folder_path.exists():
        logger.error(f"Folder not found: {folder_path}")
        sys.exit(1)
    
    logger.info(f"Scanning folder: {folder_path}")
    files = processor.find_files(folder_path, recursive, args.max_depth)
    logger.info(f"Found {len(files)} files to process")
    
    if not files:
        logger.info("No supported files found")
        return
    
    # Process files
    logger.info(f"Processing {len(files)} files...")
    results = await processor.process_files_concurrent(files, args.concurrent, args.dry_run)
    
    # Generate report
    report = processor.generate_report(results, args.output)
    
    # Try to save report file (optional)
    try:
        report_filename = f"text_extraction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.output}"
        with open(report_filename, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {report_filename}")
    except Exception as e:
        logger.warning(f"Could not save report file: {e}")
    
    # Output JSON to stdout if requested
    if args.output == "json":
        print(report)
    # Don't print anything else for JSON output to avoid extra data

if __name__ == "__main__":
    asyncio.run(main()) 