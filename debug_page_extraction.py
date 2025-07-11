#!/usr/bin/env python3
"""
Debug script to test page extraction and identify the page numbering issue.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def debug_page_extraction():
    """Debug the page extraction issue."""
    print("🔍 DEBUGGING PAGE EXTRACTION ISSUE")
    print("=" * 50)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
        
        # Initialize extractor
        settings = Settings()
        extractor = EnhancedPDFExtractor(settings)
        
        # Test with available PDF files
        test_files = [
            "/home/insulto/tore_matrix_labs/5555.pdf"
        ]
        
        for test_file in test_files:
            if Path(test_file).exists():
                print(f"\n📄 Testing with file: {test_file}")
                
                try:
                    # Test extraction
                    elements, full_text, page_texts = extractor.extract_with_perfect_correlation(test_file)
                    
                    print(f"✅ Extraction successful!")
                    print(f"   Elements: {len(elements)}")
                    print(f"   Full text length: {len(full_text)}")
                    print(f"   Page texts keys: {list(page_texts.keys())}")
                    print(f"   Page texts lengths: {[(k, len(v)) for k, v in page_texts.items()]}")
                    
                    # Check if page 1 exists
                    if 1 in page_texts:
                        print(f"✅ Page 1 found with {len(page_texts[1])} characters")
                        print(f"   First 100 chars: '{page_texts[1][:100]}...'")
                    else:
                        print(f"❌ Page 1 NOT found!")
                        
                    # Check element page numbers
                    element_pages = set(e.page_number for e in elements)
                    print(f"   Element page numbers: {sorted(element_pages)}")
                    
                    # Check for elements with page 1
                    page_1_elements = [e for e in elements if e.page_number == 1]
                    print(f"   Elements on page 1: {len(page_1_elements)}")
                    
                    if page_1_elements:
                        print(f"   First element: {page_1_elements[0]}")
                    
                    break
                    
                except Exception as e:
                    print(f"❌ Extraction failed: {e}")
                    import traceback
                    traceback.print_exc()
                    
            else:
                print(f"❌ File not found: {test_file}")
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_page_extraction()