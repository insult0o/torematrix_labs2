#!/usr/bin/env python3
"""
Test extraction on multiple pages to understand the empty content issue.
"""

import sys
import os
import json
import fitz  # PyMuPDF
from pathlib import Path

sys.path.insert(0, '/home/insulto/tore_matrix_labs')

from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
from tore_matrix_labs.config.settings import Settings

def test_extraction_multiple_pages():
    """Test extraction on multiple pages to find the empty content issue."""
    print("=== TESTING EXTRACTION ON MULTIPLE PAGES ===")
    
    # Load project data
    project_path = Path('/home/insulto/tore_matrix_labs/4.tore')
    if not project_path.exists():
        print(f"✗ Project file not found: {project_path}")
        return False
    
    with open(project_path, 'r') as f:
        project_data = json.load(f)
    
    # Get PDF path
    doc_data = project_data['documents'][0]
    pdf_path = doc_data['path']
    
    print(f"✓ PDF path: {pdf_path}")
    print(f"✓ PDF exists: {Path(pdf_path).exists()}")
    
    # Test basic PyMuPDF extraction
    print("\n--- Testing PyMuPDF directly ---")
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"✓ Total pages: {total_pages}")
        
        # Test first 5 pages
        for page_num in range(min(5, total_pages)):
            page = doc[page_num]
            text = page.get_text()
            print(f"Page {page_num + 1}: {len(text)} characters")
            if text:
                print(f"  Sample: {text[:100].replace(chr(10), ' ')}")
            else:
                print("  No text found")
        
        doc.close()
        
    except Exception as e:
        print(f"✗ PyMuPDF direct extraction failed: {e}")
        return False
    
    # Test enhanced extractor
    print("\n--- Testing Enhanced Extractor ---")
    try:
        settings = Settings()
        extractor = EnhancedPDFExtractor(settings)
        
        if hasattr(extractor, 'extract_with_perfect_correlation'):
            elements, full_text, page_texts = extractor.extract_with_perfect_correlation(pdf_path)
            print(f"✓ Enhanced extraction completed:")
            print(f"  - Elements: {len(elements)}")
            print(f"  - Full text: {len(full_text)} characters")
            print(f"  - Page texts: {len(page_texts)} pages")
            
            # Check specific pages
            for page_num in [1, 2, 3, 4, 5]:
                if page_num in page_texts:
                    text = page_texts[page_num]
                    print(f"  Page {page_num}: {len(text)} characters")
                    if text:
                        print(f"    Sample: {text[:100].replace(chr(10), ' ')}")
                    else:
                        print("    Empty text")
                else:
                    print(f"  Page {page_num}: Not found in page_texts")
        else:
            print("✗ Enhanced extractor missing extract_with_perfect_correlation method")
            
    except Exception as e:
        print(f"✗ Enhanced extraction failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_extraction_multiple_pages()