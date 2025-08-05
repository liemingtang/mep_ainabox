#!/usr/bin/env python3
"""
Simple Text Processor
Processes text files and extracts information
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_text_file(file_path: str, output_dir: str = None) -> bool:
    """Process a text file and extract information"""
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            return False
        
        logger.info(f"📄 Processing text file: {file_path}")
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic text analysis
        lines = content.split('\n')
        words = content.split()
        characters = len(content)
        
        # Create analysis results
        analysis = {
            'filename': file_path.name,
            'file_path': str(file_path),
            'processed_at': datetime.now().isoformat(),
            'statistics': {
                'lines': len(lines),
                'words': len(words),
                'characters': characters,
                'average_words_per_line': len(words) / max(len(lines), 1)
            },
            'content_preview': content[:500] + '...' if len(content) > 500 else content
        }
        
        # Save results to output directory if specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create output filename
            output_file = output_path / f"{file_path.stem}_analysis.json"
            
            import json
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"✅ Analysis saved to: {output_file}")
        else:
            # Print analysis to stdout
            logger.info("=" * 50)
            logger.info("TEXT ANALYSIS RESULTS")
            logger.info("=" * 50)
            logger.info(f"File: {file_path.name}")
            logger.info(f"Lines: {analysis['statistics']['lines']}")
            logger.info(f"Words: {analysis['statistics']['words']}")
            logger.info(f"Characters: {analysis['statistics']['characters']}")
            logger.info(f"Avg words per line: {analysis['statistics']['average_words_per_line']:.2f}")
            logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process text file {file_path}: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple text processor for MEP AI NABOX")
    parser.add_argument("file_path", help="Path to the text file to process")
    parser.add_argument("--output-dir", help="Output directory for analysis results")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file_path):
        logger.error(f"File does not exist: {args.file_path}")
        sys.exit(1)
    
    # Process the file
    success = process_text_file(args.file_path, args.output_dir)
    
    if success:
        logger.info("✅ Text processing completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Text processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 