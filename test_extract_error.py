#!/usr/bin/env python3
"""
Test to reproduce the exact "Failed to extract text from page 1: 0" error.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_extract_error():
    """Test to reproduce the exact error."""
    print("🔍 TESTING EXTRACT ERROR REPRODUCTION")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
        
        # Test with actual PDF file
        file_path = "/home/insulto/tore_matrix_labs/5555.pdf"
        if not Path(file_path).exists():
            print(f"❌ Test file not found: {file_path}")
            return
        
        settings = Settings()
        extractor = EnhancedPDFExtractor(settings)
        
        print("📄 Step 1: Test enhanced extraction directly")
        elements, full_text, page_texts = extractor.extract_with_perfect_correlation(file_path)
        
        print(f"✅ Enhanced extraction successful")
        print(f"   Elements: {len(elements)}")
        print(f"   Full text length: {len(full_text)}")
        print(f"   Page texts keys: {list(page_texts.keys())[:5]}... (showing first 5)")
        
        # Test accessing page 1 directly
        if 1 in page_texts:
            print(f"✅ Page 1 accessible: {len(page_texts[1])} characters")
        else:
            print("❌ Page 1 not accessible")
            
        # Test accessing page 0 (should fail)
        if 0 in page_texts:
            print("❌ Page 0 accessible (this is wrong)")
        else:
            print("✅ Page 0 not accessible (this is correct)")
            
        print(f"\n📄 Step 2: Test page validation widget mock")
        
        # Mock the page validation widget logic
        def mock_load_page_text_with_enhanced_extraction(page_number, file_path):
            print(f"Mock _load_page_text_with_enhanced_extraction called with page_number={page_number}")
            
            try:
                # This mimics the actual code
                elements, full_text, page_texts = extractor.extract_with_perfect_correlation(file_path)
                
                print(f"Enhanced extraction returned: {len(elements)} elements, {len(full_text)} chars total, {len(page_texts)} pages")
                print(f"Available pages in page_texts: {list(page_texts.keys())[:5]}...")
                
                # Check if page_number is in page_texts
                if page_number in page_texts:
                    page_text = page_texts[page_number]
                    print(f"✅ Found page {page_number} text: {len(page_text)} characters")
                    return page_text
                else:
                    print(f"❌ Page {page_number} not found in enhanced extraction")
                    return None
                    
            except Exception as e:
                print(f"❌ Enhanced extraction failed: {str(e)}")
                print(f"Exception type: {type(e)}")
                print(f"Exception args: {e.args}")
                raise e
        
        # Test with page 1 (should work)
        print("\n🔍 Testing with page 1:")
        result = mock_load_page_text_with_enhanced_extraction(1, file_path)
        if result:
            print(f"✅ Page 1 extraction successful: {len(result)} characters")
        else:
            print("❌ Page 1 extraction failed")
            
        # Test with page 0 (should fail gracefully)
        print("\n🔍 Testing with page 0:")
        result = mock_load_page_text_with_enhanced_extraction(0, file_path)
        if result:
            print(f"❌ Page 0 extraction unexpectedly successful: {len(result)} characters")
        else:
            print("✅ Page 0 extraction failed as expected")
            
        print(f"\n📄 Step 3: Test coordinate correspondence")
        
        # Test coordinate correspondence which converts page 1 to page 0
        def test_coordinate_correspondence():
            try:
                from tore_matrix_labs.ui.components.coordinate_correspondence import coordinate_engine
                
                # Test with page 0 (converted from page 1)
                print("Testing coordinate correspondence with page 0 (converted from page 1)...")
                
                highlight_region = coordinate_engine.find_text_coordinates(
                    pdf_path=file_path,
                    page_number=0,  # 0-indexed (converted from page 1)
                    search_text="procedural guidance",
                    fallback_bbox=[100, 200, 400, 220]
                )
                
                print(f"✅ Coordinate correspondence successful")
                print(f"   Match type: {highlight_region.match_type}")
                print(f"   Confidence: {highlight_region.confidence}")
                print(f"   Regions: {len(highlight_region.regions)}")
                
            except Exception as e:
                print(f"❌ Coordinate correspondence failed: {str(e)}")
                print(f"Exception type: {type(e)}")
                import traceback
                traceback.print_exc()
                
        test_coordinate_correspondence()
        
        print(f"\n🔍 CONCLUSION")
        print("=" * 60)
        print("Testing completed. Look for any errors above that might explain")
        print("the 'Failed to extract text from page 1: 0' error.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extract_error()